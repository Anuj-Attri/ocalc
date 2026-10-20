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



def format_table(points) -> str:
    lines = [f"{'n':>10}  {'time':>12}  {'memory':>12}"]
    for point in points:
        size = f"{point.n:d}" if point.n is not None else "-"
        lines.append(
            f"{size:>10}  {format_seconds(point.time_s):>12}  {format_bytes(point.memory_bytes):>12}"
        )
    return "\n".join(lines)





