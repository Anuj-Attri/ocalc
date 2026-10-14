import numpy as np

from ocalc.fit import fit_curve


def _noisy(y, seed):
    rng = np.random.default_rng(seed)
    return y * np.exp(rng.normal(0.0, 0.10, size=np.shape(y)))


def _sizes():
    return np.geomspace(100, 100_000, 8)


def test_recovers_linear():
    n = _sizes()
    result = fit_curve(n, _noisy(1e-8 * n, seed=1))
    assert result.label == "n"
    assert result.display == "O(n)"
    assert result.confidence == "high"


def test_recovers_linearithmic():
    n = _sizes()
    result = fit_curve(n, _noisy(1e-8 * n * np.log(n), seed=2))
    assert result.label == "n log n"
    assert result.display == "O(n log n)"
    assert result.confidence == "high"


def test_recovers_quadratic():
    n = _sizes()
    result = fit_curve(n, _noisy(1e-6 * n**2, seed=3))
    assert result.label == "n^2"
    assert result.display == "O(n^2)"
    assert result.confidence == "high"


def test_recovers_cubic():
    n = _sizes()
    result = fit_curve(n, _noisy(1e-12 * n**3, seed=4))
    assert result.label == "n^3"
    assert result.display == "O(n^3)"
    assert result.confidence == "high"


def test_recovers_logarithmic():
    n = np.geomspace(100, 1_000_000, 8)
    result = fit_curve(n, _noisy(1e-3 * np.log(n), seed=5))
    assert result.label == "log n"
    assert result.display == "O(log n)"
    assert result.confidence == "high"


def test_recovers_constant():
    n = _sizes()
    result = fit_curve(n, _noisy(np.full(n.shape, 2e-3), seed=6))
    assert result.label == "1"
    assert result.display == "O(1)"
    assert result.confidence == "high"


def test_quadratic_beats_free_polynomial():
    n = _sizes()
    result = fit_curve(n, _noisy(1e-6 * n**2, seed=7))
    assert result.label == "n^2"


def test_recovers_exponential_on_small_n():
    n = np.array([5, 8, 11, 14, 17, 20], dtype=float)
    result = fit_curve(n, _noisy(1e-6 * 2.0**n, seed=8))
    assert result.label == "c^n"
    assert result.display == "O(c^n)"


def test_exponential_flag_short_circuits():
    result = fit_curve([8.0, 12.0], [1e-3, 2e-2], exponential=True)
    assert result.label == "c^n"
    assert result.display == "O(c^n)"
    assert result.confidence == "high"


def test_too_few_points_is_inconclusive():
    result = fit_curve([10.0, 20.0, 40.0], [1.0, 2.0, 4.0])
    assert result.label == "inconclusive"
    assert result.display == "inconclusive"
    assert result.confidence == "inconclusive"


def test_nearly_linear_slope_prefers_n_over_a_close_n_log_n():
    n = [2000, 4183, 8747, 18292, 38254, 80000]
    y = np.array([18.5, 40.1, 82.2, 175, 371, 875]) * 1e-6
    result = fit_curve(n, y)
    assert result.label == "n"
    assert result.display == "O(n)"
    assert result.confidence == "low"
    assert result.runner_up == "O(n log n)"


def test_low_confidence_names_runner_up():
    # A short size range makes neighboring classes hard to separate.
    n = np.linspace(1000, 1800, 8)
    rng = np.random.default_rng(1)
    y = (1e-8 * n) * np.exp(rng.normal(0.0, 0.05, size=n.shape))
    result = fit_curve(n, y)
    assert result.confidence == "low"
    assert result.runner_up
    assert result.runner_up.startswith("O(")
