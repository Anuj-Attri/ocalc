"""Build the inputs that grow with n, and load functions from a file."""

from __future__ import annotations

import ast
import re


class NeedSample(ValueError):
    """The function needs an example call before it can be measured."""


def parse_sample(text: str) -> tuple[tuple, dict]:
    """Parse literal arguments, including keyword arguments such as factor=3."""
    text = text.strip()
    if not text:
        return (), {}
    args = []
    kwargs = {}
    try:
        for part in _split_top_level(text):
            match = re.match(r"^([A-Za-z_]\w*)\s*=\s*(.*)$", part, re.DOTALL)
            if match:
                kwargs[match.group(1)] = ast.literal_eval(match.group(2))
                continue
            if kwargs:
                raise NeedSample("Pass positional arguments before name=value arguments.")
            args.append(ast.literal_eval(part))
    except (SyntaxError, ValueError) as exc:
        raise NeedSample(
            'Sample must be Python literals. Example: --sample "[1, 2, 3], 9"'
        ) from exc
    return tuple(args), kwargs


def _split_top_level(text: str) -> list[str]:
    parts = []
    buf: list[str] = []
    depth = 0
    quote = ""
    escaped = False
    for char in text:
        if quote:
            buf.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char in {"'", '"'}:
            quote = char
            buf.append(char)
            continue
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth = max(0, depth - 1)
        if char == "," and depth == 0:
            part = "".join(buf).strip()
            if part:
                parts.append(part)
            buf = []
            continue
        buf.append(char)
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts
