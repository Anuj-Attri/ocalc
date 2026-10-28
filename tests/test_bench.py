import time
from pathlib import Path

import pytest

from ocalc import annotate_file, measure
from ocalc.bench import geometric_sizes
from ocalc.cli import main
from ocalc.generate import NeedSample, load_function, parse_sample, plan_inputs
from ocalc.mcp_server import measure_function


def test_geometric_sizes_cover_the_ends():
    sizes = geometric_sizes(100, 100_000, 8)
    assert sizes[0] == 100
    assert sizes[-1] == 100_000
    assert sizes == sorted(set(sizes))
    assert len(sizes) == 8
    assert geometric_sizes(100, 100, 8) == [100]


def test_parse_sample_literals():
    args, kwargs = parse_sample("[1, 2, 3], 9")
    assert args == ([1, 2, 3], 9)
    assert kwargs == {}
    args, _ = parse_sample("9")
    assert args == (9,)
    with pytest.raises(NeedSample):
        parse_sample("two_sum([1], 9)")


def test_mismatched_sample_follows_the_signature():
    def add(nums: list[int], b: int) -> list[int]:
        return [b + num for num in nums]

    plan = plan_inputs(add, (1, 9))
    args, kwargs = plan.build(4)
    assert plan.mode == "sized"
    assert args == ([0, 1, 2, 3], 9)
    assert kwargs == {}
    assert add(*args) == [9, 10, 11, 12]


def test_keyword_sample_and_keyword_only_parameter():
    def scale(nums: list[int], *, factor: int):
        return [factor * number for number in nums]

    args, kwargs = parse_sample("[1, 2], factor=3")
    plan = plan_inputs(scale, args, kwargs)
    built, keywords = plan.build(3)
    assert built == ([0, 1, 2],)
    assert keywords == {"factor": 3}


def test_set_dict_optional_and_string():
    def gather(items: set[int], table: dict[str, int] | None):
        return len(items) + len(table or {})

    def shout(name: str):
        return name

    plan = plan_inputs(gather)
    args, _ = plan.build(3)
    assert args[0] == {0, 1, 2}
    assert args[1] == {"0": 0}

    text = plan_inputs(shout)
    assert text.mode == "sized"
    assert text.build(4)[0] == ("aaaa",)


def test_method_and_async_function(tmp_path: Path):
    path = tmp_path / "box.py"
    path.write_text(
        "class Box:\n"
        "    def run(self, nums: list[int]):\n"
        "        return [n + 1 for n in nums]\n",
        encoding="utf-8",
    )
    method = load_function(path, "Box.run")
    plan = plan_inputs(method)
    args, _ = plan.build(3)
    assert args == ([0, 1, 2],)
    assert method(*args) == [1, 2, 3]

    async def add(a, b):
        return a + b

    report = measure(add, 1, 2, budget=1, repeats=2)
    assert "Time: O(1)" in report.comment
    assert "repeats=2" in report.comment


def test_protocol_flags_are_recorded():
    def scan(items: list[int]):
        return len(items)

    report = measure(scan, budget=1, min_n=20, max_n=80, measures=3, repeats=2)
    assert report.protocol.min_n == 20
    assert report.protocol.max_n == 80
    assert report.protocol.measures == 3
    assert report.protocol.budget == 1
    assert report.protocol.repeats == 2
    assert "repeats=2" in report.comment


def test_sample_list_scales_and_keeps_the_other_argument():
    def two_sum(nums, target):
        return target

    plan = plan_inputs(two_sum, ([1, 2], 9))
    args, kwargs = plan.build(5)
    assert args[0] == [0, 1, 2, 3, 4]
    assert args[1] == 9
    assert kwargs == {}
    assert plan.mode == "sized"


def test_single_int_scales_and_two_ints_do_not():
    def fib(n):
        return n

    def add(a, b):
        return a + b

    fib_plan = plan_inputs(fib, (10,))
    assert fib_plan.mode == "int_n"
    assert fib_plan.build(12)[0] == (12,)

    add_plan = plan_inputs(add, (1, 2))
    assert add_plan.mode == "constant"
    assert add_plan.build(100)[0] == (1, 2)


def test_hints_build_inputs_without_a_sample():
    def two_sum(nums: list, target: int):
        return target

    plan = plan_inputs(two_sum)
    args, _ = plan.build(4)
    assert args[0] == [0, 1, 2, 3]
    assert args[1] == 0


def test_string_annotations():
    def two_sum(nums: "list[int]", target: "int"):
        return target

    args, _ = plan_inputs(two_sum).build(3)
    assert args == ([0, 1, 2], 0)


def test_list_default_scales_without_a_sample():
    def scan(items=[1, 2]):
        return len(items)

    plan = plan_inputs(scan)
    assert plan.mode == "sized"
    assert plan.build(3)[0] == ([0, 1, 2],)


def test_untyped_function_asks_for_a_sample():
    def two_sum(nums, target):
        return target

    with pytest.raises(NeedSample):
        plan_inputs(two_sum)


def test_constant_function_reports_o1():
    def add(a, b):
        return a + b

    report = measure(add, 1, 2, budget=1)
    assert "Time: O(1)" in report.comment
    assert "Space: O(1)" in report.comment
    assert "at n=" not in report.comment


def test_budget_stops_a_slow_function():
    def slow(items):
        time.sleep(0.25)
        return len(items)

    started = time.perf_counter()
    report = measure(slow, [1], budget=0.6, min_n=100, max_n=100_000, measures=8)
    elapsed = time.perf_counter() - started
    assert elapsed < 3
    assert len(report.points) < 8


def test_process_timeout_stops_a_hang(tmp_path: Path):
    path = tmp_path / "hang.py"
    path.write_text("def hang():\n    while True:\n        pass\n", encoding="utf-8")
    func = load_function(path, "hang")
    started = time.perf_counter()
    with pytest.raises(RuntimeError, match="budget"):
        measure(func, budget=0.8)
    assert time.perf_counter() - started < 8


def test_annotate_replaces_the_comment_and_keeps_previous(tmp_path: Path):
    path = tmp_path / "demo.py"
    path.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    annotate_file(path, "add", 1, 2, budget=1)
    once = path.read_text(encoding="utf-8")
    assert once.startswith("# ocalc:")
    assert "Time: O(1)" in once
    annotate_file(path, "add", 1, 2, budget=1)
    twice = path.read_text(encoding="utf-8")
    assert twice.count("# ocalc:") == 1
    assert "Previous:" in twice


def test_cli_measure_and_missing_function(tmp_path: Path, capsys):
    path = tmp_path / "demo.py"
    path.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    assert main(["measure", str(path), "-f", "add", "--sample", "1, 2", "--budget", "1"]) == 0
    captured = capsys.readouterr()
    assert "Time: O(1)" in captured.out
    assert main(["measure", str(path), "-f", "missing", "--budget", "1"]) == 2


def test_mcp_measure_function_returns_the_comment(tmp_path: Path):
    path = tmp_path / "demo.py"
    path.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    text = measure_function(str(path), "add", sample="1, 2", budget=1)
    assert "Time: O(1)" in text


def test_structured_sample_keeps_record_shape():
    def total(orders, tax: int):
        return sum(order["qty"] for order in orders) + tax

    sample = [{"sku": "A1", "qty": 2}, {"sku": "B2", "qty": 3}]
    plan = plan_inputs(total, (sample, 5))
    orders, tax = plan.build(5)[0]
    assert tax == 5
    assert len(orders) == 5
    assert orders[0] == {"sku": "A1", "qty": 2}
    assert orders[1]["sku"] == "B2"
    assert orders[0] is not sample[0]
    report = measure(total, sample, 5, budget=1, min_n=20, max_n=200, measures=4, repeats=1)
    assert "Time:" in report.comment


def test_package_import_keeps_relative_imports_and_skips_main():
    import sys

    path = Path(__file__).parent / "fixtures" / "billing" / "job.py"
    func = load_function(path, "price")
    assert func([{"sku": "A1", "qty": 2}], 1) == 3
    assert sys.modules["billing.job"].RAN_MAIN is False
    report = measure(
        func,
        [{"sku": "A1", "qty": 2}],
        1,
        budget=1,
        min_n=20,
        max_n=80,
        measures=3,
        repeats=1,
    )
    assert "Time:" in report.comment


def test_missing_file_names_the_path(tmp_path: Path):
    missing = tmp_path / "missing.py"
    with pytest.raises(FileNotFoundError, match="No such file"):
        load_function(missing, "add")
