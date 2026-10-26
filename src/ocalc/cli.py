"""Command line for measuring and annotating functions."""

from __future__ import annotations

import argparse
import sys

from ocalc import FunctionNotFound, NeedSample, annotate_file, measure, parse_sample
from ocalc.comment import format_table
from ocalc.generate import load_function


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="ocalc",
        description="Measure a Python function and estimate its time and space complexity.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    measure_cmd = commands.add_parser("measure", help="Print a complexity report.")
    annotate_cmd = commands.add_parser("annotate", help="Write the complexity comment above a function.")
    for command in (measure_cmd, annotate_cmd):
        command.add_argument("file", help="Python file that defines the function.")
        command.add_argument("-f", "--function", required=True, help="Function qualname, such as two_sum.")
        command.add_argument(
            "--sample",
            default="",
            help='Literal arguments, for example "[1, 2, 3], 9".',
        )
    commands.add_parser("mcp", help="Serve the measure and annotate tools over stdio.")

    args = parser.parse_args(argv)
    if args.command == "mcp":
        from ocalc.mcp_server import serve

        serve()
        return 0
    try:
        return _run(args)
    except NeedSample as exc:
        print(exc, file=sys.stderr)
        return 2
    except FunctionNotFound as exc:
        print(exc, file=sys.stderr)
        return 2
    except (RuntimeError, OSError) as exc:
        print(exc, file=sys.stderr)
        return 1


def _run(args) -> int:
    sample_args, sample_kwargs = parse_sample(args.sample)
    if args.command == "measure":
        func = load_function(args.file, args.function)
        report = measure(
            func,
            *sample_args,
            file=args.file,
            qualname=args.function,
            **sample_kwargs,
        )
        print(format_table(report.points))
        print()
        print(report.comment)
        return 0
    report = annotate_file(args.file, args.function, *sample_args, **sample_kwargs)
    print(report.comment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
