"""Estimate complexity from source text in any language."""

from __future__ import annotations

import re
from dataclasses import dataclass

_RANK = ["O(1)", "O(log n)", "O(n)", "O(n log n)", "O(n^2)", "O(n^3)", "O(n^k)", "O(c^n)"]
_DEF = re.compile(r"\b(?:def|function|func|fn|fun)\s+([A-Za-z_]\w*)\s*\(")
_CDEF = re.compile(
    r"(?m)^[ \t]*(?:(?:public|private|protected|static|async|inline|virtual|const|override)\s+)*"
    r"(?:[\w:<>,\*&\[\]]+\s+)+([A-Za-z_]\w*)\s*\([^;]*\)\s*\{"
)
_SKIP = {"if", "for", "while", "switch", "catch", "return", "sizeof", "foreach"}
_C_LANGS = {"c", "cpp", "java", "csharp"}
_INDENT_LANGS = {"python", "ruby", "lua", "scala"}
_GROW = re.compile(
    r"\b(?:append|push|push_back|emplace|emplace_back|add)\s*\(|\bnew\s+\w+\s*\["
    r"|[\[{][^\n]*\bfor\b"
)
_LOG = re.compile(
    r"while\s+.*\b(?:low|left|lo|start)\s*<=?\s*(?:high|right|hi|end)\b"
    r"|/=\s*2|//=\s*2|>>=\s*1|=\s*\w+\s*/\s*2|=\s*\w+\s*//\s*2"
)
_HEADER = re.compile(
    r"^(?:foreach|for|while|loop|until|async\s+for)\b"
    r"|\.(?:forEach|each_with_index|each|times|flat_map|flatMap|map|filter|reduce|select)\b"
)
_PENDING = re.compile(
    r"(?:foreach|for|while|loop|until)\b"
    r"|\.(?:forEach|each_with_index|each|times|flatMap|flat_map|map|filter|reduce|select)\s*(?:\(|\{)"
)
_SCAN = re.compile(
    r"(?<!\.)\b(?:sum|map|filter|any|all)\s*\("
    r"|\b(?:np|numpy|torch)\s*\.\s*(?:sum|mean|prod)\s*\("
)
_SORT = re.compile(
    r"\bsorted\s*\(|\.(?:sort|sort_by|sort_unstable)\s*\("
    r"|\b(?:sort\.Slice|Arrays\.sort|Collections\.sort)\b|\bstd\s*::\s*sort\b"
)
_LINALG = re.compile(
    r"\b(?:matmul|matrix_power|einsum)\b|\.dot\s*\("
    r"|\blinalg\s*\.\s*(?:inv|det|eig|eigh|svd|solve|pinv|qr|cholesky)\b"
)


@dataclass(frozen=True)
class FunctionEstimate:
    name: str
    time: str
    space: str
    reason: str


@dataclass(frozen=True)
class SourceAnalysis:
    language: str
    time: str
    space: str
    detail: str
    functions: tuple[FunctionEstimate, ...] = ()


def analyze_source(source: str, language: str | None = None) -> SourceAnalysis:
    """Estimate worst-case time and space from a source snippet.

    The reported class is the worst function in the snippet. Loops, recursion,
    and calls such as matrix products and sorts set that class.

    Args:
        source: The program text.
        language: A language name such as ``python`` or ``go``. Detected when omitted.

    Returns:
        The detected language, the worst-case classes, and one row per function.
    """
    language = (language or _detect(source)).lower()
    code = _mask(source)
    bodies = _bodies(code, language)
    if not bodies:
        bodies = [("", code)]
    functions = tuple(
        FunctionEstimate(name or "snippet", *_classify(body, name, language))
        for name, body in bodies
    )
    time_fn = max(functions, key=lambda item: _RANK.index(item.time))
    space_fn = max(functions, key=lambda item: _RANK.index(item.space))
    if _RANK.index(space_fn.space) > _RANK.index(time_fn.space):
        detail = f"worst case · time {time_fn.name} · space {space_fn.name}"
    else:
        detail = f"worst case · {time_fn.name}"
    return SourceAnalysis(language, time_fn.time, space_fn.space, detail, functions)


def _detect(source: str) -> str:
    if re.search(r"<\?php\b", source):
        return "php"
    if re.search(r"^\s*fun\s+\w+\s*\(", source, re.M):
        return "kotlin"
    if re.search(r"\bfn\s+\w+\s*\(", source):
        return "rust"
    if re.search(r"\bfunc\s+\w+", source) and (":=" in source or re.search(r"\bpackage\s+\w+", source)):
        return "go"
    if re.search(r"\bfunc\s+\w+", source) and ("->" in source or re.search(r"\b(?:let|guard|var)\s+", source)):
        return "swift"
    if re.search(r"^\s*object\s+\w+", source, re.M) and re.search(r"\bdef\s+\w+", source):
        return "scala"
    if re.search(r"^\s*(?:async\s+)?def\s+\w+.*:\s*(?:#.*)?$", source, re.M) or re.search(r"\bself\b", source):
        return "python"
    if re.search(r"^\s*def\s+\w+", source, re.M) and re.search(r"^\s*end\s*$", source, re.M):
        return "ruby"
    if re.search(r"^\s*(?:local\s+)?function\b", source, re.M) and re.search(r"^\s*end\s*$", source, re.M):
        return "lua"
    if re.search(r"\bnamespace\b|\bConsole\.(?:Write|Read)", source):
        return "csharp"
    if re.search(
        r"\b(?:public|private|protected)\s+(?:static\s+)?(?:class|void|int|boolean|String|long)\b"
        r"|\bSystem\.out\b",
        source,
    ):
        return "java"
    if "#include" in source and ("std::" in source or "cout" in source or "template" in source):
        return "cpp"
    if "#include" in source or re.search(r"\bint\s+main\s*\(", source):
        return "c"
    if re.search(r"\binterface\s+\w+|\btype\s+\w+\s*=|:\s*(?:string|number|boolean)\b", source):
        return "typescript"
    if re.search(r"\bfunction\b|=>|\bconsole\.|\bconst\b|\blet\b", source):
        return "javascript"
    if re.search(r"\$\w+", source) and re.search(r"\bfunction\b", source):
        return "php"
    if source.count("{") >= source.count(":\n"):
        return "c"
    return "python"


def _mask(source: str) -> str:
    out: list[str] = []
    i = 0
    n = len(source)
    while i < n:
        ch = source[i]
        nxt = source[i + 1] if i + 1 < n else ""
        if ch in {"'", '"', "`"}:
            token = ch * 3 if source[i : i + 3] == ch * 3 else ch
            out.append(" " * len(token))
            i += len(token)
            while i < n:
                if source[i] == "\\":
                    out.append("  ")
                    i += 2
                    continue
                if source.startswith(token, i):
                    out.append(" " * len(token))
                    i += len(token)
                    break
                out.append("\n" if source[i] == "\n" else " ")
                i += 1
            continue
        if ch == "#" or (ch == "/" and nxt == "/"):
            step = 1 if ch == "#" else 2
            out.append(" " * step)
            i += step
            while i < n and source[i] != "\n":
                out.append(" ")
                i += 1
            continue
        if ch == "/" and nxt == "*":
            out.append("  ")
            i += 2
            while i < n and not (source[i] == "*" and i + 1 < n and source[i + 1] == "/"):
                out.append("\n" if source[i] == "\n" else " ")
                i += 1
            out.append("  ")
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _bodies(code: str, language: str) -> list[tuple[str, str]]:
    matches = list(_DEF.finditer(code))
    if language in _C_LANGS:
        matches += [item for item in _CDEF.finditer(code) if item.group(1) not in _SKIP]
    matches.sort(key=lambda item: item.start())
    bodies = []
    for index, match in enumerate(matches):
        name = next(group for group in match.groups() if group)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(code)
        bodies.append((name, code[start:end]))
    return bodies


def _classify(body: str, name: str, language: str) -> tuple[str, str, str]:
    nest, product, sort = _measure(body, language)
    calls = _calls(body, name)
    logarithmic = bool(_LOG.search(body)) and " for " not in f" {body} "
    if calls >= 2 and logarithmic:
        time, reason = "O(n log n)", "2 recursive calls"
    elif calls >= 2:
        time, reason = "O(c^n)", "2 recursive calls"
    elif calls == 1 and logarithmic and nest == 0:
        time, reason = "O(log n)", "1 recursive call"
    elif calls == 1 and nest == 0:
        time, reason = "O(n)", "1 recursive call"
    elif product and nest > 3:
        time, reason = "O(n^k)", "matrix product inside a loop"
    elif product:
        time, reason = "O(n^3)", "matrix product"
    elif sort and nest == 0:
        time, reason = "O(n log n)", "sort"
    elif sort:
        time, reason = "O(n^k)", "sort inside a loop"
    elif nest == 0 and logarithmic:
        time, reason = "O(log n)", "halves the range"
    elif nest <= 0:
        time, reason = "O(1)", "no loop"
    elif nest == 1 and logarithmic:
        time, reason = "O(log n)", "halves the range"
    elif nest == 1:
        time, reason = "O(n)", "1 loop"
    elif nest == 2:
        time, reason = "O(n^2)", "2 nested loops"
    elif nest == 3:
        time, reason = "O(n^3)", "3 nested loops"
    else:
        time, reason = "O(n^k)", f"{nest} nested loops"

    spaces = ["O(1)"]
    if calls >= 1 and logarithmic:
        spaces.append("O(log n)")
    elif calls >= 1:
        spaces.append("O(n)")
    if product:
        spaces.append("O(n^2)")
    if sort:
        spaces.append("O(n)")
    if _GROW.search(body) and nest >= 1:
        spaces.append({1: "O(n)", 2: "O(n^2)", 3: "O(n^3)"}.get(nest, "O(n^k)"))
    space = max(spaces, key=_RANK.index)
    return time, space, reason


def _calls(body: str, name: str) -> int:
    if not name:
        return 0
    return len(re.findall(rf"\b{re.escape(name)}\s*\(", body))


def _measure(body: str, language: str) -> tuple[int, bool, bool]:
    indent = _measure_indent(body)
    braces = _measure_braces(body)
    if language in _INDENT_LANGS:
        nest = max(indent[0], braces[0])
        return nest, indent[1] or braces[1], indent[2] or braces[2]
    return braces


def _line_facts(stripped: str) -> tuple[bool, bool, bool, bool]:
    header = bool(_HEADER.search(stripped))
    product = _LINALG.search(stripped) is not None or _matmul(stripped)
    sort = _SORT.search(stripped) is not None
    scan = (not header) and _SCAN.search(stripped) is not None
    return header, product, sort, scan


def _matmul(stripped: str) -> bool:
    if stripped.startswith("@"):
        return False
    return "@" in stripped


def _measure_indent(body: str) -> tuple[int, bool, bool]:
    stack: list[int] = []
    best = 0
    product = False
    sort = False
    for raw in body.splitlines():
        expanded = raw.expandtabs(4)
        if not expanded.strip():
            continue
        stripped = expanded.lstrip(" ")
        indent = len(expanded) - len(stripped)
        while stack and indent <= stack[-1]:
            stack.pop()
        header, line_product, line_sort, scan = _line_facts(stripped)
        product = product or line_product
        sort = sort or line_sort
        loops = len(re.findall(r"\b(?:foreach|for|while|until)\b", stripped))
        if header and re.match(r"(?:foreach|for|while|until|async\s+for)\b", stripped):
            stack.append(indent)
            loops -= 1
            best = max(best, len(stack) + max(loops, 0))
        elif header:
            stack.append(indent)
            best = max(best, len(stack) + max(loops, 0))
        elif loops:
            best = max(best, len(stack) + loops)
        if line_product:
            best = max(best, len(stack) + 3)
        elif scan:
            best = max(best, len(stack) + 1)
    return best, product, sort


def _measure_braces(body: str) -> tuple[int, bool, bool]:
    depth = 0
    loops: list[int] = []
    pending = False
    best = 0
    product = False
    sort = False
    i = 0
    n = len(body)
    while i < n:
        header = _PENDING.match(body, i)
        if header:
            pending = True
            i = header.end()
            continue
        ch = body[i]
        if ch == "\n":
            line = body[body.rfind("\n", 0, i) + 1 : i]
            stripped = line.strip()
            _, line_product, line_sort, scan = _line_facts(stripped)
            product = product or line_product
            sort = sort or line_sort
            if line_product:
                best = max(best, len(loops) + 3)
            elif scan:
                best = max(best, len(loops) + 1)
        if ch == "{":
            depth += 1
            if pending:
                loops.append(depth)
                pending = False
                best = max(best, len(loops))
        elif ch == "}":
            if loops and loops[-1] == depth:
                loops.pop()
            depth = max(0, depth - 1)
            pending = False
        elif ch == ";" and pending:
            best = max(best, len(loops) + 1)
            pending = False
        i += 1
    tail = body[body.rfind("\n") + 1 :]
    _, line_product, line_sort, scan = _line_facts(tail.strip())
    product = product or line_product
    sort = sort or line_sort
    if line_product:
        best = max(best, len(loops) + 3)
    elif scan:
        best = max(best, len(loops) + 1)
    return best, product, sort
