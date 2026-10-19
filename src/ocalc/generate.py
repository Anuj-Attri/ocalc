"""Build the inputs that grow with n, and load functions from a file."""

from __future__ import annotations

import ast
import importlib.util
import inspect
import re
import sys
import types
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Union, get_args, get_origin

_COLLECTIONS = {list, tuple, set, frozenset, dict}
_TEXT = {"str", "bytes", "bytearray"}


class NeedSample(ValueError):
    """The function needs an example call before it can be measured."""


class FunctionNotFound(LookupError):
    """The named function is not in the file."""


@dataclass
class InputPlan:
    """A recipe for calling a function at size n."""

    mode: str
    index: int | None = None
    key: str | None = None
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    kind: str = ""

    def build(self, n: int) -> tuple[tuple, dict]:
        if self.mode == "constant":
            return self.args, dict(self.kwargs)
        args = list(self.args)
        kwargs = dict(self.kwargs)
        if self.mode == "int_n":
            value: Any = int(n)
        else:
            value = _materialize(self.kind, int(n))
        if self.key is not None:
            kwargs[self.key] = value
        else:
            args[self.index] = value
        return tuple(args), kwargs


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


def plan_inputs(func, sample_args=(), sample_kwargs=None) -> InputPlan:
    """Build a call from the signature, then choose which argument grows with n."""
    func = _bind_method(func)
    parameters = _parameters(func)
    if parameters and parameters[0].name in {"self", "cls"}:
        raise NeedSample(
            f"Cannot construct an instance to measure {getattr(func, '__qualname__', func.__name__)}. "
            "Use a class that can be built with no arguments, or measure a plain function."
        )
    assigned = _assign(parameters, sample_args, dict(sample_kwargs or {}))
    args: list[Any] = []
    kwargs: dict = {}
    slots = []
    for param in parameters:
        if param.name in assigned:
            value = assigned[param.name]
            kind = _kind_from_value(value) or _sized_kind(param.annotation)
        else:
            filled = _fill(param)
            if filled is None:
                raise NeedSample(
                    f"Need a value for {func.__name__}() parameter {param.name}.\n"
                    f'Example: --sample "{_sample_example(parameters)}"'
                )
            value, kind = filled
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            kwargs[param.name] = value
            where = ("kw", param.name)
        else:
            args.append(value)
            where = ("arg", len(args) - 1)
        slots.append(
            _Slot(where, kind, _int_like(param, value, kind), param.default is not inspect.Parameter.empty)
        )
    return _plan_from_slots(tuple(args), kwargs, slots)


def load_function(file, qualname: str):
    """Import a function or method from a Python file by its qualname."""
    path = Path(file).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"No such file: {path}")
    parent = str(path.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    module_name = f"ocalc_target_{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise FunctionNotFound(f"Cannot import {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    obj = module
    for part in qualname.split("."):
        if not hasattr(obj, part):
            raise FunctionNotFound(f"Cannot find {qualname} in {path.name}")
        obj = getattr(obj, part)
    if not callable(obj):
        raise FunctionNotFound(f"{qualname} is not callable")
    return _bind_method(obj)









def callable_location(func) -> tuple[str | None, str | None]:
    """Return the file and qualname when the function can be re-imported."""
    code = getattr(func, "__code__", None)
    if code is None:
        return None, None
    path = code.co_filename
    qualname = getattr(func, "__qualname__", "")
    if not path or path.startswith("<") or "<" in qualname:
        return None, None
    return path, qualname


@dataclass(frozen=True)
class _Slot:
    where: tuple
    kind: str | None
    int_like: bool
    has_default: bool


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


def _bind_method(func):
    """Return a bound method when the class can be constructed with no arguments."""
    if inspect.ismethod(func) or not inspect.isfunction(func):
        return func
    try:
        parameters = list(inspect.signature(func).parameters)
    except (TypeError, ValueError):
        return func
    if not parameters or parameters[0] not in {"self", "cls"} or "." not in func.__qualname__:
        return func
    owner = _lookup_owner(func)
    if not isinstance(owner, type):
        return func
    if parameters[0] == "cls":
        return getattr(owner, func.__name__)
    try:
        instance = owner()
    except Exception as exc:
        raise NeedSample(
            f"Cannot construct {owner.__name__}() to measure {func.__qualname__}. "
            "Use a class that can be built with no arguments, or measure a plain function."
        ) from exc
    return getattr(instance, func.__name__)


def _lookup_owner(func):
    parent: Any = func.__globals__
    for part in func.__qualname__.split(".")[:-1]:
        if isinstance(parent, dict):
            parent = parent.get(part)
        else:
            parent = getattr(parent, part, None)
        if parent is None:
            return None
    return parent


def _parameters(func):
    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError) as exc:
        raise NeedSample("Cannot read the function signature. Pass --sample.") from exc
    return [
        param
        for param in signature.parameters.values()
        if param.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        )
    ]


def _assign(parameters, sample_args, sample_kwargs) -> dict:
    assigned = dict(sample_kwargs)
    positional = [param for param in parameters if param.kind != inspect.Parameter.KEYWORD_ONLY]
    skipped = []
    index = 0
    for param in positional:
        if param.name in assigned or index >= len(sample_args):
            continue
        value = sample_args[index]
        index += 1
        if _compatible(param, value):
            assigned[param.name] = value
        else:
            skipped.append(value)
    for param in parameters:
        if param.name in assigned:
            continue
        for position, value in enumerate(skipped):
            if _compatible(param, value):
                assigned[param.name] = value
                del skipped[position]
                break
    return assigned


def _compatible(param, value) -> bool:
    annotation = _concrete(param.annotation)
    if annotation is None:
        return True
    kind = _sized_kind_body(annotation)
    if kind is not None:
        value_kind = _kind_from_value(value)
        return value_kind is not None and value_kind.split("-", 1)[0] == kind.split("-", 1)[0]
    if annotation is int:
        return _is_int(value)
    if annotation is float:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if annotation is bool:
        return isinstance(value, bool)
    if annotation is str:
        return isinstance(value, str)
    return True


def _fill(param):
    annotation = _concrete(param.annotation)
    kind = _sized_kind_body(annotation)
    if kind is None and param.default is not inspect.Parameter.empty:
        kind = _kind_from_value(param.default)
        if kind is not None:
            return param.default, kind
    if kind is not None:
        return _materialize(kind, 1), kind
    if annotation is int or (
        param.default is not inspect.Parameter.empty and _is_int(param.default)
    ):
        if param.default is not inspect.Parameter.empty and _is_int(param.default):
            return int(param.default), None
        return 0, None
    if param.default is not inspect.Parameter.empty:
        return param.default, _kind_from_value(param.default)
    if annotation is float:
        return 0.0, None
    if annotation is bool:
        return False, None
    if annotation is type(None):
        return None, None
    return None


def _int_like(param, value, kind) -> bool:
    if kind:
        return False
    annotation = _concrete(param.annotation)
    if annotation is int:
        return True
    return annotation is None and _is_int(value)


def _plan_from_slots(args, kwargs, slots: list[_Slot]) -> InputPlan:
    collections = [slot for slot in slots if _is_collection(slot.kind)]
    texts = [slot for slot in slots if slot.kind in _TEXT]
    ints = [slot for slot in slots if slot.int_like]
    chosen = None
    mode = "constant"
    if collections:
        chosen = collections[0]
        mode = "sized"
    elif len(ints) == 1 and texts and all(slot.has_default for slot in texts):
        chosen = ints[0]
        mode = "int_n"
    elif texts and not ints:
        chosen = texts[0]
        mode = "sized"
    elif len(ints) == 1:
        chosen = ints[0]
        mode = "int_n"
    if chosen is None:
        return InputPlan("constant", args=args, kwargs=kwargs)
    where, name = chosen.where
    if where == "kw":
        return InputPlan(mode, key=name, args=args, kwargs=kwargs, kind=chosen.kind or "")
    return InputPlan(mode, index=name, args=args, kwargs=kwargs, kind=chosen.kind or "")


def _is_collection(kind: str | None) -> bool:
    return bool(kind) and kind not in _TEXT


def _sample_example(parameters) -> str:
    parts = []
    for param in parameters:
        annotation = _normalize_annotation(param.annotation)
        kind = _sized_kind(annotation)
        if kind is None and param.default is not inspect.Parameter.empty:
            kind = _kind_from_value(param.default)
        if kind == "str":
            parts.append('"abc"')
        elif kind and kind.startswith("tuple"):
            parts.append("(1, 2, 3)")
        elif kind and kind.startswith("set"):
            parts.append("{1, 2, 3}")
        elif kind and kind.startswith("dict"):
            parts.append("{'a': 1}")
        elif kind:
            parts.append("[1, 2, 3]")
        elif annotation is int or (
            param.default is not inspect.Parameter.empty and _is_int(param.default)
        ):
            parts.append("9")
        else:
            parts.append("...")
    return ", ".join(parts)


def _normalize_annotation(annotation):
    if annotation is inspect.Parameter.empty or annotation is None:
        return None
    if not isinstance(annotation, str):
        return annotation
    text = annotation.strip().replace(" ", "")
    text = text.replace("|None", "")
    if text.startswith("Optional[") and text.endswith("]"):
        text = text[len("Optional[") : -1]
    basics = {
        "int": int,
        "str": str,
        "bytes": bytes,
        "bytearray": bytearray,
        "float": float,
        "bool": bool,
        "list": list,
        "List": list,
        "tuple": tuple,
        "Tuple": tuple,
        "set": set,
        "Set": set,
        "frozenset": frozenset,
        "dict": dict,
        "Dict": dict,
    }
    if text in basics:
        return basics[text]
    named = {"int": int, "str": str, "float": float, "bytes": bytes}
    match = re.fullmatch(r"(list|List|Sequence|Iterable|tuple|Tuple|set|Set|frozenset)\[(\w+)\]", text)
    if match:
        outer_name = match.group(1)
        outer = {"tuple": tuple, "Tuple": tuple, "set": set, "Set": set, "frozenset": frozenset}.get(
            outer_name, list
        )
        return outer[named.get(match.group(2), int)]
    match = re.fullmatch(r"(dict|Dict)\[(\w+),(\w+)\]", text)
    if match:
        return dict[named.get(match.group(2), int), named.get(match.group(3), int)]
    return text


def _concrete(annotation):
    annotation = _normalize_annotation(annotation)
    if annotation is None:
        return None
    origin = get_origin(annotation)
    if origin is Union or origin is types.UnionType:
        choices = [_normalize_annotation(arg) for arg in get_args(annotation) if arg is not type(None)]
        sized = [choice for choice in choices if _sized_kind_body(choice)]
        if sized:
            return sized[0]
        return choices[0] if choices else None
    return annotation


def _sized_kind(annotation) -> str | None:
    return _sized_kind_body(_concrete(annotation))


def _sized_kind_body(annotation) -> str | None:
    if annotation is None or isinstance(annotation, str):
        return None
    if annotation is str:
        return "str"
    if annotation is bytes:
        return "bytes"
    if annotation is bytearray:
        return "bytearray"
    origin = get_origin(annotation)
    if annotation in _COLLECTIONS:
        origin = annotation
        arguments = ()
    else:
        arguments = get_args(annotation) if origin is not None else ()
    if origin in {Sequence, Iterable}:
        origin = list
    if origin not in _COLLECTIONS:
        return None
    element = arguments[0] if arguments else int
    if isinstance(element, str):
        element = _normalize_annotation(element)
    if element is str:
        name = "str"
    elif element is float:
        name = "float"
    else:
        name = "int"
    containers = {tuple: "tuple", set: "set", frozenset: "frozenset", dict: "dict"}
    return f"{containers.get(origin, 'list')}-{name}"


def _kind_from_value(value) -> str | None:
    if isinstance(value, str):
        return "str"
    if isinstance(value, bytearray):
        return "bytearray"
    if isinstance(value, bytes):
        return "bytes"
    if isinstance(value, tuple):
        return "tuple-" + _element_name(value[0] if value else 0)
    if isinstance(value, list):
        return "list-" + _element_name(value[0] if value else 0)
    if isinstance(value, frozenset):
        return "frozenset-" + _element_name(next(iter(value), 0))
    if isinstance(value, set):
        return "set-" + _element_name(next(iter(value), 0))
    if isinstance(value, dict):
        return "dict-" + _element_name(next(iter(value), 0))
    return None


def _element_name(element) -> str:
    if isinstance(element, str):
        return "str"
    if isinstance(element, float) and not isinstance(element, bool):
        return "float"
    return "int"


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _materialize(kind: str, n: int):
    n = max(int(n), 0)
    if kind == "str":
        return "a" * n
    if kind == "bytes":
        return b"a" * n
    if kind == "bytearray":
        return bytearray(b"a" * n)
    container, element = kind.split("-", 1)
    if element == "str":
        data = ["a"] * n
    elif element == "float":
        data = [float(i % 1000) for i in range(n)]
    else:
        data = list(range(n))
    if container == "tuple":
        return tuple(data)
    if container in {"set", "frozenset"} and element == "str":
        data = [str(i) for i in range(n)]
    if container == "set":
        return set(data)
    if container == "frozenset":
        return frozenset(data)
    if container == "dict":
        if element == "str":
            return {str(i): i for i in range(n)}
        return {item: item for item in data}
    return data
