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
