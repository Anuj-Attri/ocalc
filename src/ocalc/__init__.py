"""Measure a Python function and estimate its time and space complexity."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ocalc.bench import BenchResult, Point, benchmark
from ocalc.comment import (
    Protocol,
    format_comment,
    format_table,
)
from ocalc.fit import FitResult, fit_curve
from ocalc.generate import (
    FunctionNotFound,
    NeedSample,
    callable_location,
    load_function,
    parse_sample,
    plan_inputs,
)

__version__ = "0.1.0"

__all__ = [
    "FunctionNotFound",
    "NeedSample",
    "Report",
    "measure",
    "parse_sample",
]


@dataclass(frozen=True)
class Report:
    comment: str
    points: list[Point]
    time: FitResult
    space: FitResult
    worst_s: float
    median_s: float
    worst_n: int | None
    protocol: Protocol


def measure(
    func,
    *sample_args,
    budget: float | None = None,
    min_n: int | None = None,
    max_n: int | None = None,
    measures: int | None = None,
    repeats: int | None = None,
    file: str | None = None,
    qualname: str | None = None,
    protocol: Protocol | None = None,
    previous_s: float | None = None,
    **sample_kwargs,
) -> Report:
    """Run a bounded benchmark and return the complexity comment plus the table rows."""
    plan = plan_inputs(func, sample_args, sample_kwargs)
    if protocol is not None and protocol.constant and plan.mode == "constant":
        if budget is None:
            budget = protocol.budget
        if repeats is None:
            repeats = protocol.repeats
    elif protocol is not None and not protocol.constant and plan.mode != "constant":
        if budget is None:
            budget = protocol.budget
        if min_n is None:
            min_n = protocol.min_n
        if max_n is None:
            max_n = protocol.max_n
        if measures is None:
            measures = protocol.measures
        if repeats is None:
            repeats = protocol.repeats

    located_file, located_name = callable_location(func)
    file = file or located_file
    qualname = qualname or located_name
    result = benchmark(
        func,
        plan,
        budget=5.0 if budget is None else budget,
        min_n=min_n,
        max_n=max_n,
        measures=measures,
        repeats=repeats,
        file=file,
        qualname=qualname,
    )
    time_fit, space_fit = _fits(result)
    comment = format_comment(
        time=time_fit,
        space=space_fit,
        worst_s=result.worst_s,
        worst_n=result.worst_n,
        median_s=result.median_s,
        protocol=result.protocol,
        previous_s=previous_s,
    )
    return Report(
        comment=comment,
        points=result.points,
        time=time_fit,
        space=space_fit,
        worst_s=result.worst_s,
        median_s=result.median_s,
        worst_n=result.worst_n,
        protocol=result.protocol,
    )



def _fits(result: BenchResult) -> tuple[FitResult, FitResult]:
    if result.constant:
        done = FitResult("1", "O(1)", "high")
        return done, done
    sizes = [point.n for point in result.points]
    times = [point.time_s for point in result.points]
    time_fit = fit_curve(sizes, times, exponential=result.exponential)
    return time_fit, _space_fit(sizes, [point.memory_bytes for point in result.points])


def _space_fit(sizes, memory) -> FitResult:
    used = np.asarray(memory, dtype=float)
    if used.size == 0 or np.nanmax(used) <= 0:
        return FitResult("1", "O(1)", "high")
    positive = used[used > 0]
    floor = float(positive.min()) if positive.size else 1.0
    used = np.where(used > 0, used, floor)
    return fit_curve(sizes, used)
