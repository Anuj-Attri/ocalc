# ocalc

`ocalc` measures a Python function and writes a one-line estimate of its time and space complexity.

```python
# ocalc: Time: O(n); Space: O(1); Worst: 0.42 s at n=100000; Median: 0.31 s; Confidence: high; Protocol: min_n=100,max_n=100000,measures=8,budget=5,repeats=5
def two_sum(nums, target):
    ...
```

The class is whichever of these formulas fits the measurements: `1`, `log n`, `n`, `n log n`, `n^2`, `n^3`, `n^k`, `c^n`. **Worst** is the slowest size that finished in this run, at that `n`. It is a repeatable measurement, not a proof, and it is not a search for adversarial inputs.

Run it again after a change. The next comment reuses the same sizes and keeps the old worst time as `Previous`, so you can see whether the function got faster on the same machine.

## Install

From a checkout:

```bash
pip install -e .
```

The core package depends on NumPy. The editor tools are optional:

```bash
pip install -e ".[mcp]"
```

From GitHub:

```bash
pip install "git+https://github.com/Anuj-Attri/ocalc.git"
```

## Command line

```bash
ocalc measure FILE -f two_sum --sample "[1, 2, 3], 9"
ocalc annotate FILE -f two_sum --sample "[1, 2, 3], 9"
```

`measure` prints the size table and the comment. `annotate` writes the comment above the function and replaces an older ocalc comment. Nothing runs because a file was saved. You ask, then the tool runs.

Protocol flags, with their defaults:

```bash
ocalc measure FILE -f two_sum --sample "[1, 2, 3], 9" --min-n 100 --max-n 20000 --measures 6 --budget 3 --repeats 3
```

`--budget` is seconds to spend (5). `--min-n` and `--max-n` are the size grid (100 and 100000, or 8 and 100000 when the only input is an int). `--measures` is how many sizes to try (8). `--repeats` is how many timed calls to make at each size (5). A later annotate reuses the protocol stored in the comment unless you pass a flag.

The first list, tuple, set, dict, or bytes argument grows with `n`. A lone string grows when it is the input. A single int, as in `fib(n)`, is `n`. Other arguments stay at the sample or the type hint. Keyword arguments are written `factor=3`. A sample that does not match a hint is not forced into that parameter: `add(nums: list[int], b: int)` with `--sample "1, 9"` still grows a list and keeps an int.

`--sample` accepts Python literals only. It is not executed as code. A function with nothing to grow is called as written and reported as `O(1)`. Methods are measured when the class can be constructed with no arguments. `async def` functions are awaited.

A list of numbers becomes `0 .. n-1`. A sample of records, such as a list of dicts, is copied until it has `n` items, and each copy keeps the sample's keys and nested values. A file inside a package is imported as that package, so relative imports keep working. Code under `if __name__ == "__main__"` does not run. The measurement runs on the machine where you invoke `ocalc`. The test suite runs on GitHub Actions.

## Python

```python
from ocalc import measure

def two_sum(nums: list, target: int):
    seen = {}
    for index, value in enumerate(nums):
        if target - value in seen:
            return [seen[target - value], index]
        seen[value] = index
    return []

report = measure(two_sum, [1, 2, 3], 9)
print(report.comment)
```

Type hints are enough when they say what to grow. `list`, `set`, and `dict` plus an `int` grow the collection and keep the int fixed. A single `int` argument, as in `fib(n)`, is the size. Two plain ints are called as given. Pass `repeats=`, `min_n=`, `max_n=`, `measures=`, and `budget=` to `measure` to change the protocol.

## Cursor MCP

Install the extra, then add this to the project MCP config:

```json
{
  "mcpServers": {
    "ocalc": {
      "command": "ocalc",
      "args": ["mcp"]
    }
  }
}
```

The server exposes `measure_function` and `annotate_function`. Ask the agent to annotate a function. The same budget and timeout rules apply.

## What the numbers mean

The benchmark builds each input before the timer starts. It takes the median of a few calls at each size, stops when the next size would use up the budget, and kills a call that exceeds the time limit when the function was loaded from a file. Memory is the `tracemalloc` peak of one call, which is Python allocations, not the whole process.

Confidence is high, medium, low, or inconclusive. Low names the runner-up class. Inconclusive means too few sizes finished, or none of the formulas fit.

## Limits

- The tool executes the function, including side effects, imports, and loops. The timeout bounds a single call when the function lives in a file.
- A list or dict of numbers is generated. A sample of records is repeated to length `n`. A branch that only shows up on data outside that sample will not show up here.
- The budget can stop a slow function before the asymptotic shape is visible. The report then says the fit is inconclusive, or exponential when the time blew up while `n` was still small.
- `tracemalloc` misses some growth that lives only on the C stack.
- A method is measured by constructing its class with no arguments. If that constructor needs arguments, measure a plain function instead.

## Development

```bash
pip install -e ".[dev]"
pytest
```
