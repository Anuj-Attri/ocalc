import json
import shutil
import subprocess
from pathlib import Path

from ocalc.static import analyze_source


def test_constant_snippet():
    result = analyze_source("def ready():\n    return 1\n")
    assert result.language == "python"
    assert result.time == "O(1)"
    assert result.space == "O(1)"


def test_one_python_loop_is_linear():
    source = "def scan(items):\n    total = 0\n    for item in items:\n        total += item\n    return total\n"
    result = analyze_source(source)
    assert result.time == "O(n)"
    assert result.space == "O(1)"


def test_nested_python_loops_are_quadratic():
    source = (
        "def pairs(rows):\n"
        "    count = 0\n"
        "    for row in rows:\n"
        "        for value in row:\n"
        "            count += 1\n"
        "    return count\n"
    )
    assert analyze_source(source).time == "O(n^2)"


def test_list_comprehension_allocates():
    source = "def scale(items):\n    return [2 * item for item in items]\n"
    result = analyze_source(source)
    assert result.time == "O(n)"
    assert result.space == "O(n)"


def test_python_append_uses_linear_space():
    source = "def grow(items):\n    out = []\n    for item in items:\n        out.append(item)\n    return out\n"
    result = analyze_source(source)
    assert result.time == "O(n)"
    assert result.space == "O(n)"


def test_binary_search_is_logarithmic():
    source = (
        "def search(nums, target):\n"
        "    low = 0\n"
        "    high = len(nums) - 1\n"
        "    while low <= high:\n"
        "        mid = (low + high) // 2\n"
        "        if nums[mid] == target:\n"
        "            return mid\n"
        "        if nums[mid] < target:\n"
        "            low = mid + 1\n"
        "        else:\n"
        "            high = mid - 1\n"
        "    return -1\n"
    )
    assert analyze_source(source).time == "O(log n)"


def test_double_recursion_is_exponential():
    source = "def fib(n):\n    if n < 2:\n        return n\n    return fib(n - 1) + fib(n - 2)\n"
    result = analyze_source(source)
    assert result.time == "O(c^n)"
    assert result.space == "O(n)"


def test_javascript_loop():
    source = "function sum(items) {\n  let total = 0;\n  for (let i = 0; i < items.length; i++) {\n    total += items[i];\n  }\n  return total;\n}\n"
    result = analyze_source(source)
    assert result.language == "javascript"
    assert result.time == "O(n)"


def test_go_loop():
    source = "package main\nfunc sum(nums []int) int {\n  total := 0\n  for i := 0; i < len(nums); i++ {\n    total += nums[i]\n  }\n  return total\n}\n"
    result = analyze_source(source, language="go")
    assert result.time == "O(n)"
    assert result.space == "O(1)"


def test_matrix_product_is_cubic_and_labeled_worst_case():
    source = (
        'def gemm(x, w):\n'
        '    """Multiply ``x`` and ``w`` as ``x @ w``.\n'
        '    for row in x:\n'
        '        for col in w:\n'
        '            pass\n'
        '    """\n'
        '    return x @ w\n'
    )
    result = analyze_source(source)
    assert result.time == "O(n^3)"
    assert result.space == "O(n^2)"
    assert result.detail == "worst case · gemm"
    assert result.functions[0].reason == "matrix product"


def test_string_and_docstring_do_not_count_as_loops():
    source = 'def ready():\n    label = "for item in items"\n    return 1\n'
    assert analyze_source(source).time == "O(1)"


def test_tab_indented_loops_are_nested():
    source = "def pairs(rows):\n\tfor row in rows:\n\t\tfor value in row:\n\t\t\tpass\n"
    assert analyze_source(source).time == "O(n^2)"


def test_worst_function_is_named():
    source = (
        "def ready():\n"
        "    return 1\n"
        "\n"
        "def pairs(rows):\n"
        "    for row in rows:\n"
        "        for value in row:\n"
        "            pass\n"
    )
    result = analyze_source(source)
    assert result.time == "O(n^2)"
    assert result.space == "O(1)"
    assert result.detail == "worst case · pairs"
    assert [item.name for item in result.functions] == ["ready", "pairs"]


def test_sort_is_n_log_n():
    source = "def ordered(items):\n    return sorted(items)\n"
    result = analyze_source(source)
    assert result.time == "O(n log n)"
    assert result.space == "O(n)"
    assert result.functions[0].reason == "sort"


def test_scan_builtin_is_linear():
    source = "def total(items):\n    return sum(items)\n"
    assert analyze_source(source).time == "O(n)"


def test_scan_inside_a_loop_is_quadratic():
    source = "def total(rows):\n    acc = 0\n    for row in rows:\n        acc += sum(row)\n    return acc\n"
    assert analyze_source(source).time == "O(n^2)"


def test_javascript_for_each():
    source = "function sum(items) {\n  let total = 0;\n  items.forEach(item => { total += item; });\n  return total;\n}\n"
    result = analyze_source(source)
    assert result.language == "javascript"
    assert result.time == "O(n)"


def test_sequential_loops_stay_linear():
    source = (
        "function sum(items) {\n"
        "  let total = 0;\n"
        "  items.forEach(item => { total += item; });\n"
        "  items.forEach(item => { total += item; });\n"
        "  return total;\n"
        "}\n"
    )
    assert analyze_source(source).time == "O(n)"


def test_rust_java_ruby_kotlin_and_c():
    rust = "fn sum(nums: &[i32]) -> i32 {\n    let mut total = 0;\n    for n in nums {\n        total += n;\n    }\n    total\n}\n"
    java = "class T {\n  public int sum(int[] items) {\n    int total = 0;\n    for (int i = 0; i < items.length; i++) {\n      total += items[i];\n    }\n    return total;\n  }\n}\n"
    ruby = "def pairs(rows)\n  rows.each do |row|\n    row.each do |value|\n      value\n    end\n  end\nend\n"
    kotlin = "fun sum(nums: List<Int>): Int {\n  var total = 0\n  for (n in nums) {\n    total += n\n  }\n  return total\n}\n"
    c = "#include <stdio.h>\nint sum(int *nums, int n) {\n  int total = 0;\n  for (int i = 0; i < n; i++) {\n    total += nums[i];\n  }\n  return total;\n}\n"
    assert analyze_source(rust).language == "rust"
    assert analyze_source(rust).time == "O(n)"
    assert analyze_source(java).language == "java"
    assert analyze_source(java).time == "O(n)"
    assert analyze_source(ruby).language == "ruby"
    assert analyze_source(ruby).time == "O(n^2)"
    assert analyze_source(kotlin).language == "kotlin"
    assert analyze_source(kotlin).time == "O(n)"
    assert analyze_source(c).language == "c"
    assert analyze_source(c).time == "O(n)"


def test_typescript_php_cpp_csharp_swift_and_lua():
    typescript = "function sum(items: number[]): number {\n  let total = 0;\n  for (const n of items) {\n    total += n;\n  }\n  return total;\n}\n"
    php = "<?php\nfunction sum($nums) {\n  $total = 0;\n  foreach ($nums as $n) {\n    $total += $n;\n  }\n  return $total;\n}\n"
    cpp = "#include <iostream>\nint sum(const std::vector<int>& nums) {\n  int total = 0;\n  for (int n : nums) {\n    total += n;\n  }\n  return total;\n}\n"
    csharp = "namespace T {\n  public int Sum(int[] items) {\n    int total = 0;\n    foreach (var n in items) {\n      total += n;\n    }\n    return total;\n  }\n}\n"
    swift = "func sum(nums: [Int]) -> Int {\n  var total = 0\n  for n in nums {\n    total += n\n  }\n  return total\n}\n"
    lua = "function sum(nums)\n  local total = 0\n  for _, n in ipairs(nums) do\n    total = total + n\n  end\n  return total\nend\n"
    samples = {
        "typescript": typescript,
        "php": php,
        "cpp": cpp,
        "csharp": csharp,
        "swift": swift,
        "lua": lua,
    }
    for language, source in samples.items():
        result = analyze_source(source)
        assert result.language == language, result.language
        assert result.time == "O(n)", (language, result.time, result.functions)


def test_browser_analyzer_matches_python():
    node = shutil.which("node")
    if not node:
        return
    samples = [
        "def ready():\n    return 1\n",
        "def scan(items):\n    total = 0\n    for item in items:\n        total += item\n    return total\n",
        "def pairs(rows):\n    count = 0\n    for row in rows:\n        for value in row:\n            count += 1\n    return count\n",
        "def grow(items):\n    out = []\n    for item in items:\n        out.append(item)\n    return out\n",
        "def search(nums, target):\n    low = 0\n    high = len(nums) - 1\n    while low <= high:\n        mid = (low + high) // 2\n        if nums[mid] == target:\n            return mid\n        if nums[mid] < target:\n            low = mid + 1\n        else:\n            high = mid - 1\n    return -1\n",
        "def fib(n):\n    if n < 2:\n        return n\n    return fib(n - 1) + fib(n - 2)\n",
        "function sum(items) {\n  let total = 0;\n  for (let i = 0; i < items.length; i++) {\n    total += items[i];\n  }\n  return total;\n}\n",
        "package main\nfunc sum(nums []int) int {\n  total := 0\n  for i := 0; i < len(nums); i++ {\n    total += nums[i]\n  }\n  return total\n}\n",
        'def gemm(x, w):\n    """for row in x:\n    """\n    return x @ w\n',
        "def pairs(rows):\n\tfor row in rows:\n\t\tfor value in row:\n\t\t\tpass\n",
        "def ready():\n    return 1\n\ndef pairs(rows):\n    for row in rows:\n        for value in row:\n            pass\n",
        "def ordered(items):\n    return sorted(items)\n",
        "def total(items):\n    return sum(items)\n",
        "def scale(items):\n    return [2 * item for item in items]\n",
        "function sum(items) {\n  let total = 0;\n  items.forEach(item => { total += item; });\n  return total;\n}\n",
        "fn sum(nums: &[i32]) -> i32 {\n    let mut total = 0;\n    for n in nums {\n        total += n;\n    }\n    total\n}\n",
        "def pairs(rows)\n  rows.each do |row|\n    row.each do |value|\n      value\n    end\n  end\nend\n",
        "fun sum(nums: List<Int>): Int {\n  var total = 0\n  for (n in nums) {\n    total += n\n  }\n  return total\n}\n",
    ]
    expected = []
    for source in samples:
        result = analyze_source(source)
        expected.append(
            {
                "language": result.language,
                "time": result.time,
                "space": result.space,
                "detail": result.detail,
                "functions": [
                    {"name": item.name, "time": item.time, "space": item.space, "reason": item.reason}
                    for item in result.functions
                ],
            }
        )
    script = r"""
const fs = require("fs");
const vm = require("vm");
const context = { globalThis: {} };
context.globalThis = context;
vm.createContext(context);
vm.runInContext(fs.readFileSync(process.argv[1], "utf8"), context);
const samples = JSON.parse(fs.readFileSync(0, "utf8"));
const out = samples.map((source) => context.analyzeSource(source));
process.stdout.write(JSON.stringify(out));
"""
    path = Path(__file__).parents[1] / "docs" / "_extra" / "analyze.js"
    completed = subprocess.run(
        [node, "-e", script, str(path)],
        input=json.dumps(samples),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == expected
