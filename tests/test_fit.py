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
