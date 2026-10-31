# ocalc

`ocalc` measures a Python function and writes a one-line estimate of its time and space complexity.

```python
# ocalc: Time: O(n); Space: O(1); Worst: 0.42 s at n=100000; Median: 0.31 s; Confidence: high; Protocol: min_n=100,max_n=100000,measures=8,budget=5,repeats=5
def two_sum(nums, target):
    ...
```

## Install

```bash
pip install ocalc
pip install "ocalc[mcp]"
```

## Use

```bash
ocalc measure FILE -f two_sum --sample "[1, 2, 3], 9"
ocalc annotate FILE -f two_sum --sample "[1, 2, 3], 9"
```

![ocalc annotate writes the measured comment above the function](https://raw.githubusercontent.com/Anuj-Attri/ocalc/main/docs/images/annotate.png)

Try a snippet on the [demo](https://anuj-attri.github.io/ocalc/demo.html). The page reports the worst case in the file. The guide and API reference are at [anuj-attri.github.io/ocalc](https://anuj-attri.github.io/ocalc/).

## Development

```bash
pip install -e ".[dev,docs]"
pytest
sphinx-build -b html docs docs/_build/html
```
