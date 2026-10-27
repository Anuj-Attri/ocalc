"""Stdio MCP tools that measure a function or write its complexity comment."""

from __future__ import annotations

import sys

from ocalc import annotate_file, measure, parse_sample
from ocalc.comment import format_metrics, format_table
from ocalc.generate import load_function


def measure_function(
    file: str,
    function: str,
    sample: str = "",
    budget: float = 5.0,
    min_n: int | None = None,
    max_n: int | None = None,
    measures: int | None = None,
    repeats: int | None = None,
) -> str:
    """Benchmark a function and return its complexity comment.

    The tool runs the function. It stops at the time budget and does not search
    for adversarial inputs. Worst is the slowest completed size.

    file: path to the Python file.
    function: qualname, for example two_sum or Box.run.
    sample: literal arguments, for example [1, 2, 3], 9.
    budget: seconds to spend measuring.
    """
    args, kwargs = parse_sample(sample)
    func = load_function(file, function)
    report = measure(
        func,
        *args,
        budget=budget,
        min_n=min_n,
        max_n=max_n,
        measures=measures,
        repeats=repeats,
        file=file,
        qualname=function,
        **kwargs,
    )
    return format_table(report.points) + "\n\n" + format_metrics(report.comment)


def annotate_function(
    file: str,
    function: str,
    sample: str = "",
    budget: float = 5.0,
    min_n: int | None = None,
    max_n: int | None = None,
    measures: int | None = None,
    repeats: int | None = None,
) -> str:
    """Benchmark a function and write the complexity comment above it.

    A later call reuses the same sizes and records the previous worst time,
    so a code change can be compared on the same machine.

    file: path to the Python file.
    function: qualname, for example two_sum.
    sample: literal arguments, for example [1, 2, 3], 9.
    budget: seconds to spend measuring.
    """
    args, kwargs = parse_sample(sample)
    report = annotate_file(
        file,
        function,
        *args,
        budget=budget,
        min_n=min_n,
        max_n=max_n,
        measures=measures,
        repeats=repeats,
        **kwargs,
    )
    return format_metrics(report.comment)


def serve() -> None:
    """Run the stdio MCP server. Requires the ocalc[mcp] extra."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        sys.stderr.write('The MCP extra is not installed. Run: pip install "ocalc[mcp]"\n')
        raise SystemExit(1) from None
    server = FastMCP("ocalc")
    server.tool()(measure_function)
    server.tool()(annotate_function)
    server.run()
