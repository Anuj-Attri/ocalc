"""Time a function across a size grid and record peak Python allocations."""

from __future__ import annotations

import asyncio
import inspect
import math
import multiprocessing
import time
import tracemalloc
from dataclasses import dataclass
from statistics import median

from ocalc.comment import Protocol
from ocalc.generate import InputPlan, load_function

DEFAULT_BUDGET = 5.0
DEFAULT_MEASURES = 8
DEFAULT_MIN_N = 100
DEFAULT_MAX_N = 100_000
DEFAULT_MIN_N_INT = 8
_REPEATS = 5


@dataclass(frozen=True)
class Point:
    n: int | None
    time_s: float
    memory_bytes: float


@dataclass
class BenchResult:
    points: list[Point]
    protocol: Protocol
    exponential: bool
    constant: bool
    timed_out: bool
    worst_s: float
    median_s: float
    worst_n: int | None


def geometric_sizes(min_n: int, max_n: int, measures: int) -> list[int]:
    """Evenly spaced sizes on a log scale, including both ends."""
    if measures < 1:
        raise ValueError("measures must be at least 1")
    if min_n > max_n:
        raise ValueError("min_n cannot be greater than max_n")
    if measures == 1 or min_n == max_n:
        return [int(max_n)]
    ratio = (max_n / min_n) ** (1 / (measures - 1))
    raw = [int(round(min_n * ratio**i)) for i in range(measures)]
    raw[0] = int(min_n)
    raw[-1] = int(max_n)
    sizes: list[int] = []
    for size in raw:
        size = max(int(min_n), size)
        if not sizes or size > sizes[-1]:
            sizes.append(size)
    if sizes[-1] != int(max_n):
        sizes.append(int(max_n))
    return sizes


def benchmark(
    func,
    plan: InputPlan,
    *,
    budget: float,
    min_n: int | None,
    max_n: int | None,
    measures: int | None,
    repeats: int | None,
    file: str | None,
    qualname: str | None,
) -> BenchResult:
    measures = DEFAULT_MEASURES if measures is None else measures
    budget = DEFAULT_BUDGET if budget is None else budget
    repeats = _REPEATS if repeats is None else max(1, int(repeats))
    if plan.mode == "constant":
        return _benchmark_constant(func, plan, budget, repeats, file, qualname)

    if plan.mode == "int_n":
        min_n = DEFAULT_MIN_N_INT if min_n is None else min_n
        max_n = DEFAULT_MAX_N if max_n is None else max_n
    else:
        min_n = DEFAULT_MIN_N if min_n is None else min_n
        max_n = DEFAULT_MAX_N if max_n is None else max_n
    protocol = Protocol(int(min_n), int(max_n), int(measures), float(budget), repeats=repeats)
    sizes = geometric_sizes(protocol.min_n, protocol.max_n, protocol.measures)
    points: list[Point] = []
    exponential = False
    timed_out = False
    started = time.perf_counter()

    for size in sizes:
        remaining = budget - (time.perf_counter() - started)
        if remaining <= 0.05:
            break
        if len(points) >= 2 and _explosive(
            points[-2].n, points[-2].time_s, points[-1].n, points[-1].time_s
        ):
            exponential = True
            break
        if points:
            ratio = size / points[-1].n
            predicted = points[-1].time_s * max(ratio, 1.0) ** 2
            if predicted > remaining:
                break
        args, kwargs = plan.build(size)
        status, times, peak = _measure_call(
            func,
            args,
            kwargs,
            file=file,
            qualname=qualname,
            repeats=repeats,
            timeout=max(0.2, remaining),
        )
        if status == "timeout":
            timed_out = True
            if points and (
                points[-1].n <= 40
                and points[-1].time_s > 1e-4
                or (
                    len(points) >= 2
                    and _explosive(points[-2].n, points[-2].time_s, points[-1].n, points[-1].time_s)
                )
            ):
                exponential = True
            break
        if status == "error":
            raise RuntimeError(times)
        point = Point(size, float(median(times)), float(peak))
        points.append(point)
        if len(points) >= 2 and _explosive(
            points[-2].n, points[-2].time_s, points[-1].n, points[-1].time_s
        ):
            exponential = True
            break

    if not points:
        raise RuntimeError(
            "No measurement finished within the budget. Raise --budget or lower --min-n."
        )
    slowest = max(points, key=lambda item: item.time_s)
    return BenchResult(
        points=points,
        protocol=protocol,
        exponential=exponential,
        constant=False,
        timed_out=timed_out,
        worst_s=slowest.time_s,
        median_s=float(median(item.time_s for item in points)),
        worst_n=slowest.n,
    )


def _benchmark_constant(func, plan, budget, repeats, file, qualname) -> BenchResult:
    args, kwargs = plan.build(0)
    status, times, peak = _measure_call(
        func,
        args,
        kwargs,
        file=file,
        qualname=qualname,
        repeats=repeats,
        timeout=max(0.2, budget),
    )
    if status == "timeout":
        raise RuntimeError(
            "No measurement finished within the budget. Raise --budget or lower --min-n."
        )
    if status == "error":
        raise RuntimeError(times)
    protocol = Protocol(0, 0, 0, float(budget), constant=True, repeats=repeats)
    point = Point(None, float(median(times)), float(peak))
    return BenchResult(
        points=[point],
        protocol=protocol,
        exponential=False,
        constant=True,
        timed_out=False,
        worst_s=float(max(times)),
        median_s=float(median(times)),
        worst_n=None,
    )


def _explosive(n0, t0, n1, t1) -> bool:
    if t0 <= 0 or t1 <= 0 or n1 <= n0:
        return False
    n_ratio = n1 / n0
    t_ratio = t1 / t0
    if n_ratio < 1.5 and t_ratio > 2 and n1 <= 64 and t1 > 1e-4:
        return True
    if t1 < 1e-3 or n_ratio <= 1:
        return False
    exponent = math.log(t_ratio) / math.log(n_ratio)
    return exponent > 5


def _call(func, args, kwargs):
    result = func(*args, **kwargs)
    if inspect.iscoroutine(result):
        return asyncio.run(result)
    return result


def _measure_call(func, args, kwargs, *, file, qualname, repeats, timeout):
    times, peak = collect_sample(func, args, kwargs, repeats)
    return "ok", times, peak


def collect_sample(func, args, kwargs, repeats: int = _REPEATS):
    """Warm up, time several calls, then record one tracemalloc peak."""
    _call(func, args, kwargs)
    batch = 1

    def once() -> float:
        started = time.perf_counter()
        for _ in range(batch):
            _call(func, args, kwargs)
        return (time.perf_counter() - started) / batch

    first = once()
    if first < 0.001:
        batch = min(10_000, max(1, math.ceil(0.002 / max(first, 1e-9))))
        first = once()
    times = [first]
    if first <= 0.2:
        for _ in range(repeats - 1):
            duration = once()
            times.append(duration)
            if duration > 0.2:
                break
    tracemalloc.start()
    try:
        _call(func, args, kwargs)
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return times, float(peak)



