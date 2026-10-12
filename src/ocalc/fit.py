"""Fit measured curves to the eight common complexity formulas."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FitResult:
    label: str
    display: str
    confidence: str
    runner_up: str | None = None


def fit_curve(ns, ys, *, exponential: bool = False) -> FitResult:
    """Choose the formula that best matches the measured curve."""
    return FitResult("inconclusive", "inconclusive", "inconclusive")
