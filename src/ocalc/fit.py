"""Fit measured curves to the eight common complexity formulas."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

_ORDER = ("1", "log n", "n", "n log n", "n^2", "n^3", "n^k", "c^n")
_DISPLAY = {
    "1": "O(1)",
    "log n": "O(log n)",
    "n": "O(n)",
    "n log n": "O(n log n)",
    "n^2": "O(n^2)",
    "n^3": "O(n^3)",
    "c^n": "O(c^n)",
    "inconclusive": "inconclusive",
}


@dataclass(frozen=True)
class FitResult:
    label: str
    display: str
    confidence: str
    runner_up: str | None = None
    rmse: float | None = None
    k: float | None = None


@dataclass(frozen=True)
class _Candidate:
    label: str
    aic: float
    rmse: float
    params: int
    k: float | None = None

    @property
    def display(self) -> str:
        return _display(self.label, self.k)


def fit_curve(ns, ys, *, exponential: bool = False) -> FitResult:
    """Choose the formula a + b*f(n), b >= 0, with the best relative fit.

    exponential=True records an early stop from the benchmark, where the
    curve blew up before a full size grid could be measured.
    """
    if exponential:
        return FitResult("c^n", "O(c^n)", "high")

    n, y = _clean(ns, ys)
    if len(n) < 4:
        return _inconclusive()

    candidates = _candidates(n, y)
    if not candidates:
        return _inconclusive()


    best = min(candidates, key=lambda item: item.aic)
    if best.rmse >= 0.5:
        return _inconclusive(best.rmse)

    window = [item for item in candidates if item.aic <= best.aic + 2.0]
    chosen = min(window, key=lambda item: (item.params, _ORDER.index(item.label)))
    if chosen.rmse >= 0.5:
        return _inconclusive(chosen.rmse)

    rivals = [item for item in candidates if item.label != chosen.label]
    if not rivals:
        gap = math.inf
        runner_up = None
    else:
        rival = min(rivals, key=lambda item: item.aic)
        gap = rival.aic - chosen.aic
        runner_up = rival.display


    confidence = _confidence(chosen.rmse, gap)
    return FitResult(
        chosen.label,
        chosen.display,
        confidence,
        runner_up=runner_up if confidence == "low" else None,
        rmse=chosen.rmse,
        k=chosen.k,
    )


def _clean(ns, ys) -> tuple[np.ndarray, np.ndarray]:
    n = np.asarray(ns, dtype=float).reshape(-1)
    y = np.asarray(ys, dtype=float).reshape(-1)
    if len(n) != len(y):
        raise ValueError("sizes and measurements must have the same length")
    keep = np.isfinite(n) & np.isfinite(y) & (n > 1) & (y > 0)
    return n[keep], y[keep]


def _candidates(n: np.ndarray, y: np.ndarray) -> list[_Candidate]:
    found = []
    specs = (
        ("1", np.ones_like(n), 1, True, None),
        ("log n", np.log(n), 2, False, None),
        ("n", n, 2, False, None),
        ("n log n", n * np.log(n), 2, False, None),
        ("n^2", n**2, 2, False, None),
        ("n^3", n**3, 2, False, None),
    )
    for label, feature, params, constant, k in specs:
        item = _score(y, feature, label, params, constant=constant, k=k)
        if item is not None:
            found.append(item)

    polynomial = _best_parameter(
        n,
        y,
        label="n^k",
        values=[float(k) for k in np.arange(0.5, 8.01, 0.25) if all(abs(k - known) >= 0.2 for known in (1, 2, 3))],
        feature=lambda k: n**k,
    )
    if polynomial is not None:
        found.append(polynomial)

    if float(np.max(n)) <= 60:
        bases = [float(c) for c in np.linspace(0.02, 2.0, 80)]
        bases.append(math.log(2))
        exponential = _best_parameter(
            n,
            y,
            label="c^n",
            values=bases,
            feature=lambda c: np.exp(c * n),
        )
        if exponential is not None:
            found.append(exponential)
    return found


def _best_parameter(n, y, *, label, values, feature) -> _Candidate | None:
    best = None
    for value in values:
        column = np.asarray(feature(value), dtype=float)
        if not np.isfinite(column).all() or np.max(np.abs(column)) > 1e14:
            continue
        item = _score(y, column, label, 3, constant=False, k=float(value))
        if item is not None and (best is None or item.aic < best.aic):
            best = item
    return best


def _score(y, feature, label, params, *, constant, k) -> _Candidate | None:
    fitted = _fit_ab(y, feature, constant=constant)
    if fitted is None:
        return None
    rss, rmse = fitted
    penalty = len(y) * math.log(max(rss, 1e-18) / len(y)) + 2 * params
    return _Candidate(label, penalty, rmse, params, k)


def _fit_ab(y, feature, *, constant: bool) -> tuple[float, float] | None:
    y = np.asarray(y, dtype=float)
    weight = 1.0 / np.maximum(y, 1e-15)
    if constant:
        intercept = float(np.sum(weight) / np.sum(weight * weight))
        predicted = np.full_like(y, intercept)
    else:
        column = np.asarray(feature, dtype=float)
        scale = float(np.max(np.abs(column)))
        if not np.isfinite(scale) or scale == 0:
            return None
        column = column / scale
        design = np.column_stack([weight, column * weight])
        coefficient, *_ = np.linalg.lstsq(design, np.ones_like(y), rcond=None)
        slope = float(coefficient[1])
        if slope < 0 or not np.isfinite(slope):
            return None
        predicted = float(coefficient[0]) + slope * column
    if np.any(predicted <= 0) or not np.isfinite(predicted).all():
        return None
    residual = (y - predicted) / y
    rss = float(np.sum(residual**2))
    rmse = float(np.sqrt(np.mean(residual**2)))
    if not np.isfinite(rmse):
        return None
    return rss, rmse




def _confidence(rmse: float, gap: float) -> str:
    if rmse < 0.15 and gap > 4:
        return "high"
    if rmse < 0.35 and gap > 2:
        return "medium"
    return "low"


def _display(label: str, k: float | None) -> str:
    if label == "n^k":
        if k is None:
            return "O(n^k)"
        if abs(k - round(k)) < 0.05:
            return f"O(n^{int(round(k))})"
        return f"O(n^{k:.3g})"
    return _DISPLAY[label]


def _inconclusive(rmse: float | None = None) -> FitResult:
    return FitResult("inconclusive", "inconclusive", "inconclusive", rmse=rmse)
