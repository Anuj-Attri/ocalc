"""Render and rewrite the one-line complexity comment."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass

from ocalc.fit import FitResult
from ocalc.generate import FunctionNotFound

_DURATION = re.compile(r"([0-9]*\.?[0-9]+(?:[eE][-+]?\d+)?)\s*(us|ms|s)\b")
_WORST = re.compile(
    r"Worst:\s*([0-9]*\.?[0-9]+(?:[eE][-+]?\d+)?)\s*(us|ms|s)\b(?:\s+at n=(\d+))?"
)
_PROTOCOL = re.compile(
    r"Protocol:\s*(?:constant,budget=(?P<cbudget>[0-9.eE+-]+)(?:,repeats=(?P<crepeats>\d+))?"
    r"|min_n=(?P<min_n>\d+),max_n=(?P<max_n>\d+),measures=(?P<measures>\d+),"
    r"budget=(?P<budget>[0-9.eE+-]+)(?:,repeats=(?P<repeats>\d+))?)"
)
_SCALES = {"us": 1e-6, "ms": 1e-3, "s": 1.0}


@dataclass(frozen=True)
class Protocol:
    min_n: int
    max_n: int
    measures: int
    budget: float
    constant: bool = False
    repeats: int = 5

    def text(self) -> str:
        budget = format(self.budget, ".6g")
        if self.constant:
            return f"constant,budget={budget},repeats={self.repeats}"
        return (
            f"min_n={self.min_n},max_n={self.max_n},"
            f"measures={self.measures},budget={budget},repeats={self.repeats}"
        )


@dataclass(frozen=True)
class ParsedComment:
    worst_s: float | None
    protocol: Protocol | None


def format_seconds(seconds: float) -> str:
    if seconds >= 0.01:
        return f"{seconds:.3g} s"
    if seconds >= 1e-4:
        return f"{seconds * 1e3:.3g} ms"
    return f"{seconds * 1e6:.3g} us"


def format_bytes(amount: float) -> str:
    amount = float(amount)
    if amount < 1024:
        return f"{amount:.0f} B"
    if amount < 1024 * 1024:
        return f"{amount / 1024:.1f} KB"
    return f"{amount / 1024 / 1024:.1f} MB"


def parse_duration(text: str) -> float:
    match = _DURATION.search(text)
    if match is None:
        raise ValueError(f"Cannot read a duration from {text!r}")
    return float(match.group(1)) * _SCALES[match.group(2)]


def format_comment(
    *,
    time: FitResult,
    space: FitResult,
    worst_s: float,
    worst_n: int | None,
    median_s: float,
    protocol: Protocol,
    previous_s: float | None = None,
) -> str:
    if time.confidence == "low" and time.runner_up:
        confidence = f"low (close to {time.runner_up})"
    else:
        confidence = time.confidence
    worst = format_seconds(worst_s)
    if worst_n is not None:
        worst = f"{worst} at n={worst_n}"
    parts = [
        f"Time: {time.display}",
        f"Space: {space.display}",
        f"Worst: {worst}",
        f"Median: {format_seconds(median_s)}",
        f"Confidence: {confidence}",
    ]
    if previous_s is not None:
        parts.append(f"Previous: {format_seconds(previous_s)}")
    parts.append(f"Protocol: {protocol.text()}")
    return "# ocalc: " + "; ".join(parts)


def format_metrics(comment: str) -> str:
    """One field per line, for the terminal and the MCP reply."""
    body = comment.strip()
    prefix = "# ocalc:"
    if body.startswith(prefix):
        body = body[len(prefix) :].strip()
    return "\n".join(part.strip() for part in body.split(";") if part.strip())


def format_table(points) -> str:
    lines = [f"{'n':>10}  {'time':>12}  {'memory':>12}"]
    for point in points:
        size = f"{point.n:d}" if point.n is not None else "-"
        lines.append(
            f"{size:>10}  {format_seconds(point.time_s):>12}  {format_bytes(point.memory_bytes):>12}"
        )
    return "\n".join(lines)


def parse_comment(line: str) -> ParsedComment | None:
    if "ocalc:" not in line:
        return None
    worst = _WORST.search(line)
    worst_s = None
    if worst is not None:
        worst_s = float(worst.group(1)) * _SCALES[worst.group(2)]
    protocol = None
    found = _PROTOCOL.search(line)
    if found is not None:
        if found.group("cbudget") is not None:
            protocol = Protocol(
                0,
                0,
                0,
                float(found.group("cbudget")),
                constant=True,
                repeats=int(found.group("crepeats") or 5),
            )
        else:
            protocol = Protocol(
                int(found.group("min_n")),
                int(found.group("max_n")),
                int(found.group("measures")),
                float(found.group("budget")),
                repeats=int(found.group("repeats") or 5),
            )
    return ParsedComment(worst_s, protocol)


def apply_comment(source: str, qualname: str, comment: str) -> str:
    """Insert or replace the ocalc comment directly above a function."""
    newline = "\r\n" if "\r\n" in source else "\n"
    lines = source.splitlines()
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise FunctionNotFound(f"Cannot parse the file: {exc}") from exc
    node = _find_function(tree, qualname)
    if node is None:
        raise FunctionNotFound(f"Cannot find {qualname}")
    insert_at = node.lineno
    if node.decorator_list:
        insert_at = min(decorator.lineno for decorator in node.decorator_list)
    indent = re.match(r"[ \t]*", lines[node.lineno - 1]).group(0)
    content = comment.strip()
    if not content.startswith("#"):
        content = "# ocalc: " + content
    new_line = indent + content.lstrip()
    slot = insert_at - 2
    while slot >= 0 and lines[slot].strip() == "":
        slot -= 1
    if slot >= 0 and lines[slot].lstrip().startswith("# ocalc:"):
        lines[slot] = new_line
    else:
        lines.insert(insert_at - 1, new_line)
    text = newline.join(lines)
    if source.endswith(("\n", "\r\n")):
        text += newline
    return text


def existing_comment(source: str, qualname: str) -> ParsedComment | None:
    """Read the ocalc comment already sitting above a function, if there is one."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    node = _find_function(tree, qualname)
    if node is None:
        return None
    lines = source.splitlines()
    insert_at = node.lineno
    if node.decorator_list:
        insert_at = min(decorator.lineno for decorator in node.decorator_list)
    slot = insert_at - 2
    while slot >= 0 and lines[slot].strip() == "":
        slot -= 1
    if slot < 0 or not lines[slot].lstrip().startswith("# ocalc:"):
        return None
    return parse_comment(lines[slot])


def _find_function(tree: ast.AST, qualname: str):
    found = {}

    class Finder(ast.NodeVisitor):
        def __init__(self):
            self.stack: list[str] = []

        def visit_ClassDef(self, node: ast.ClassDef):
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef):
            self._function(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
            self._function(node)

        def _function(self, node):
            self.stack.append(node.name)
            found[".".join(self.stack)] = node
            self.generic_visit(node)
            self.stack.pop()

    Finder().visit(tree)
    return found.get(qualname)
