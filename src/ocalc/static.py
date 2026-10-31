"""Estimate complexity from source text in any language."""

from __future__ import annotations

import re
from dataclasses import dataclass

_RANK = ["O(1)", "O(log n)", "O(n)", "O(n log n)", "O(n^2)", "O(n^3)", "O(n^k)", "O(c^n)"]
_DEF = re.compile(r"\b(?:def|function|func|fn|fun)\s+([A-Za-z_]\w*)\s*\(")
_CDEF = re.compile(
    r"(?m)^[ \t]*(?:(?:public|private|protected|static|async|inline|virtual|const)\s+)*"
    r"(?:[\w:<>,\*&\[\]]+\s+)+([A-Za-z_]\w*)\s*\([^;]*\)\s*\{"
)
_SKIP = {"if", "for", "while", "switch", "catch", "return", "sizeof"}
_GROW = re.compile(
    r"\b(?:append|push|push_back|emplace|emplace_back|add)\s*\(|\bnew\s+\w+\s*\["
)
_LOG = re.compile(
    r"while\s+.*\b(?:low|left|lo|start)\s*<=?\s*(?:high|right|hi|end)\b"
    r"|/=\s*2|//=\s*2|>>=\s*1|=\s*\w+\s*/\s*2|=\s*\w+\s*//\s*2"
)


@dataclass(frozen=True)
class SourceAnalysis:
    language: str
    time: str
    space: str
    detail: str


def analyze_source(source: str, language: str | None = None) -> SourceAnalysis:
    """Estimate time and space complexity from a source snippet.

    Args:
        source: The program text.
        language: A language name such as ``python`` or ``go``. Detected when omitted.

    Returns:
        The detected language and the estimated classes.
    """
    language = (language or _detect(source)).lower()
    code = _mask(source)
    bodies = _bodies(code, language)
    if not bodies:
        bodies = [("", code)]
    best_time = "O(1)"
    best_space = "O(1)"
    for name, body in bodies:
        time, space = _classify(body, name, language)
        if _RANK.index(time) > _RANK.index(best_time):
            best_time = time
        if _RANK.index(space) > _RANK.index(best_space):
            best_space = space
    detail = f"{len(bodies)} function" + ("" if len(bodies) == 1 else "s")
    return SourceAnalysis(language, best_time, best_space, detail)


def _detect(source: str) -> str:
    if re.search(r"^\s*def\s+\w+\s*\(", source, re.M) or re.search(r"\bself\b", source):
        return "python"
    if re.search(r"\bpackage\s+main\b|\bfunc\s+", source):
        return "go"
    if re.search(r"\bfn\s+\w+\s*\(", source):
        return "rust"
    if re.search(r"#include\b|\bint\s+main\s*\(", source):
        return "c"
    if re.search(r"\bpublic\s+class\b|\bSystem\.out\b", source):
        return "java"
    if re.search(r"\bfunction\b|=>|\bconsole\.|\bconst\b|\blet\b", source):
        return "javascript"
    if source.count("{") >= source.count(":\n"):
        return "c"
    return "python"


def _mask(source: str) -> str:
    out: list[str] = []
    i = 0
    n = len(source)
    while i < n:
        ch = source[i]
        nxt = source[i + 1] if i + 1 < n else ""
        if ch in {"'", '"', "`"}:
            quote = ch
            out.append(" ")
            i += 1
            while i < n:
                if source[i] == "\\":
                    out.append("  ")
                    i += 2
                    continue
                if source[i] == quote:
                    out.append(" ")
                    i += 1
                    break
                out.append("\n" if source[i] == "\n" else " ")
                i += 1
            continue
        if ch == "#" or (ch == "/" and nxt == "/"):
            step = 1 if ch == "#" else 2
            out.append(" " * step)
            i += step
            while i < n and source[i] != "\n":
                out.append(" ")
                i += 1
            continue
        if ch == "/" and nxt == "*":
            out.append("  ")
            i += 2
            while i < n and not (source[i] == "*" and i + 1 < n and source[i + 1] == "/"):
                out.append("\n" if source[i] == "\n" else " ")
                i += 1
            out.append("  ")
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _bodies(code: str, language: str) -> list[tuple[str, str]]:
    matches = list(_DEF.finditer(code))
    if language in {"c", "java", "cpp", "csharp"}:
        matches += [item for item in _CDEF.finditer(code) if item.group(1) not in _SKIP]
    matches.sort(key=lambda item: item.start())
    bodies = []
    for index, match in enumerate(matches):
        name = next(group for group in match.groups() if group)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(code)
        bodies.append((name, code[start:end]))
    return bodies


def _classify(body: str, name: str, language: str) -> tuple[str, str]:
    nest = _nest(body, language)
    calls = _calls(body, name)
    logarithmic = bool(_LOG.search(body)) and " for " not in f" {body} "
    if calls >= 2 and logarithmic:
        time = "O(n log n)"
    elif calls >= 2:
        time = "O(c^n)"
    elif calls == 1 and logarithmic and nest == 0:
        time = "O(log n)"
    elif calls == 1 and nest == 0:
        time = "O(n)"
    elif nest == 0 and logarithmic:
        time = "O(log n)"
    elif nest <= 0:
        time = "O(1)"
    elif nest == 1 and logarithmic:
        time = "O(log n)"
    elif nest == 1:
        time = "O(n)"
    elif nest == 2:
        time = "O(n^2)"
    elif nest == 3:
        time = "O(n^3)"
    else:
        time = "O(n^k)"

    if calls >= 1 and logarithmic:
        space = "O(log n)"
    elif calls >= 1:
        space = "O(n)"
    elif _GROW.search(body) and nest >= 1:
        space = {1: "O(n)", 2: "O(n^2)", 3: "O(n^3)"}.get(nest, "O(n^k)")
    else:
        space = "O(1)"
    return time, space


def _calls(body: str, name: str) -> int:
    if not name:
        return 0
    return len(re.findall(rf"\b{re.escape(name)}\s*\(", body))


def _nest(body: str, language: str) -> int:
    if language == "python":
        return _nest_indent(body)
    return max(_nest_braces(body), _nest_indent(body) if language == "ruby" else 0)


def _nest_indent(body: str) -> int:
    stack: list[int] = []
    best = 0
    for line in body.splitlines():
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        while stack and indent <= stack[-1]:
            stack.pop()
        stripped = line.strip()
        loops = len(re.findall(r"\b(?:for|while)\b", stripped))
        if re.match(r"(?:for|while|async\s+for)\b", stripped):
            stack.append(indent)
            loops -= 1
            best = max(best, len(stack) + max(loops, 0))
        elif loops:
            best = max(best, len(stack) + loops)
    return best


def _nest_braces(body: str) -> int:
    depth = 0
    loops: list[int] = []
    pending = False
    best = 0
    i = 0
    n = len(body)
    while i < n:
        if re.match(r"(?:for|while|loop)\b", body[i:]):
            pending = True
            i += 1
            continue
        ch = body[i]
        if ch == "{":
            depth += 1
            if pending:
                loops.append(depth)
                pending = False
                best = max(best, len(loops))
        elif ch == "}":
            if loops and loops[-1] == depth:
                loops.pop()
            depth = max(0, depth - 1)
            pending = False
        elif ch == ";" and pending:
            best = max(best, len(loops) + 1)
            pending = False
        i += 1
    return best
