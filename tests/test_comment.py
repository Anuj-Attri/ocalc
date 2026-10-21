import pytest

from ocalc.comment import (
    FunctionNotFound,
    Protocol,
    apply_comment,
    format_comment,
    format_metrics,
    format_seconds,
    parse_comment,
    parse_duration,
)
from ocalc.fit import FitResult


def _line(**overrides) -> str:
    protocol = overrides.pop("protocol", Protocol(100, 100_000, 8, 5))
    values = dict(
        time=FitResult("n", "O(n)", "high"),
        space=FitResult("1", "O(1)", "high"),
        worst_s=0.42,
        worst_n=100_000,
        median_s=0.31,
        protocol=protocol,
        previous_s=None,
    )
    values.update(overrides)
    return format_comment(**values)


def test_comment_records_class_time_and_protocol():
    line = _line(previous_s=0.88)
    assert line == (
        "# ocalc: Time: O(n); Space: O(1); Worst: 0.42 s at n=100000; "
        "Median: 0.31 s; Confidence: high; Previous: 0.88 s; "
        "Protocol: min_n=100,max_n=100000,measures=8,budget=5,repeats=5"
    )


def test_printed_metrics_are_one_per_line():
    text = format_metrics(_line(previous_s=0.88))
    assert text.splitlines() == [
        "Time: O(n)",
        "Space: O(1)",
        "Worst: 0.42 s at n=100000",
        "Median: 0.31 s",
        "Confidence: high",
        "Previous: 0.88 s",
        "Protocol: min_n=100,max_n=100000,measures=8,budget=5,repeats=5",
    ]


def test_low_confidence_names_the_runner_up():
    line = _line(time=FitResult("n", "O(n)", "low", runner_up="O(n log n)"))
    assert "Confidence: low (close to O(n log n))" in line


def test_constant_comment_has_no_size():
    line = _line(
        time=FitResult("1", "O(1)", "high"),
        worst_s=1.5e-5,
        worst_n=None,
        median_s=1.2e-5,
        protocol=Protocol(0, 0, 0, 5, constant=True),
    )
    assert "at n=" not in line
    assert "Protocol: constant,budget=5,repeats=5" in line


def test_parse_round_trip():
    parsed = parse_comment(_line(previous_s=0.88))
    assert parsed is not None
    assert parsed.worst_s == pytest.approx(0.42)
    assert parsed.protocol is not None
    assert parsed.protocol.min_n == 100
    assert parsed.protocol.max_n == 100_000
    assert parsed.protocol.measures == 8
    assert parsed.protocol.budget == pytest.approx(5)


def test_duration_round_trip():
    for seconds in (0.42, 0.88, 0.31, 1.5e-5, 2.5e-3):
        assert parse_duration(format_seconds(seconds)) == pytest.approx(seconds, rel=1e-2)


def test_insert_and_replace_comment():
    source = "def two_sum(nums, target):\n    return []\n"
    first = apply_comment(source, "two_sum", _line(previous_s=None, worst_s=0.88, median_s=0.5))
    assert first.startswith("# ocalc:")
    assert "Worst: 0.88 s" in first
    parsed = parse_comment(first.splitlines()[0])
    second = apply_comment(
        first,
        "two_sum",
        _line(previous_s=parsed.worst_s, worst_s=0.42),
    )
    assert second.count("# ocalc:") == 1
    assert "Previous: 0.88 s" in second
    assert "Worst: 0.42 s" in second


def test_comment_sits_above_decorators_and_methods():
    source = "def deco(fn):\n    return fn\n\n@deco\ndef f():\n    return 1\n"
    updated = apply_comment(source, "f", _line())
    assert updated.index("# ocalc:") < updated.index("@deco")

    method = "class Box:\n    async def run(self):\n        return 1\n"
    updated = apply_comment(method, "Box.run", _line())
    assert "    # ocalc:" in updated
    assert updated.index("# ocalc:") < updated.index("async def run")


def test_missing_function():
    with pytest.raises(FunctionNotFound):
        apply_comment("def other():\n    return 1\n", "missing", _line())
