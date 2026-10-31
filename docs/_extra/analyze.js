const RANK = ["O(1)", "O(log n)", "O(n)", "O(n log n)", "O(n^2)", "O(n^3)", "O(n^k)", "O(c^n)"];
const C_LANGS = new Set(["c", "cpp", "java", "csharp"]);
const INDENT_LANGS = new Set(["python", "ruby", "lua", "scala"]);
const SKIP = new Set(["if", "for", "while", "switch", "catch", "return", "sizeof", "foreach"]);

const DEF = /\b(?:def|function|func|fn|fun)\s+([A-Za-z_]\w*)\s*\(/g;
const CDEF = /^[ \t]*(?:(?:public|private|protected|static|async|inline|virtual|const|override)\s+)*(?:[\w:<>,*&[\]]+\s+)+([A-Za-z_]\w*)\s*\([^;]*\)\s*\{/gm;
const GROW = /\b(?:append|push|push_back|emplace|emplace_back|add)\s*\(|\bnew\s+\w+\s*\[|[\[{][^\n]*\bfor\b/;
const LOG = /while\s+.*\b(?:low|left|lo|start)\s*<=?\s*(?:high|right|hi|end)\b|\/=\s*2|\/\/=\s*2|>>=\s*1|=\s*\w+\s*\/\s*2|=\s*\w+\s*\/\/\s*2/;
const HEADER = /^(?:foreach|for|while|loop|until|async\s+for)\b|\.(?:forEach|each_with_index|each|times|flat_map|flatMap|map|filter|reduce|select)\b/;
const PENDING = /^(?:(?:foreach|for|while|loop|until)\b|\.(?:forEach|each_with_index|each|times|flatMap|flat_map|map|filter|reduce|select)\s*(?:\(|\{))/;
const WORD_LOOP = /^(?:foreach|for|while|until|async\s+for)\b/;
const LOOP_WORDS = /\b(?:foreach|for|while|until)\b/g;
const SCAN = /(?<!\.)\b(?:sum|map|filter|any|all)\s*\(|\b(?:np|numpy|torch)\s*\.\s*(?:sum|mean|prod)\s*\(/;
const SORT = /\bsorted\s*\(|\.(?:sort|sort_by|sort_unstable)\s*\(|\b(?:sort\.Slice|Arrays\.sort|Collections\.sort)\b|\bstd\s*::\s*sort\b/;
const LINALG = /\b(?:matmul|matrix_power|einsum)\b|\.dot\s*\(|\blinalg\s*\.\s*(?:inv|det|eig|eigh|svd|solve|pinv|qr|cholesky)\b/;

function analyzeSource(source, language) {
  language = (language || detect(source)).toLowerCase();
  const code = mask(source);
  let bodies = bodiesOf(code, language);
  if (!bodies.length) bodies = [["", code]];
  const functions = bodies.map(([name, body]) => {
    const [time, space, reason] = classify(body, name, language);
    return { name: name || "snippet", time, space, reason };
  });
  const timeFn = functions.reduce((best, item) => (RANK.indexOf(item.time) > RANK.indexOf(best.time) ? item : best));
  const spaceFn = functions.reduce((best, item) => (RANK.indexOf(item.space) > RANK.indexOf(best.space) ? item : best));
  const detail = RANK.indexOf(spaceFn.space) > RANK.indexOf(timeFn.space)
    ? `worst case · time ${timeFn.name} · space ${spaceFn.name}`
    : `worst case · ${timeFn.name}`;
  return { language, time: timeFn.time, space: spaceFn.space, detail, functions };
}

function detect(source) {
  if (/<\?php\b/.test(source)) return "php";
  if (/^\s*fun\s+\w+\s*\(/m.test(source)) return "kotlin";
  if (/\bfn\s+\w+\s*\(/.test(source)) return "rust";
  if (/\bfunc\s+\w+/.test(source) && (/:=/.test(source) || /\bpackage\s+\w+/.test(source))) return "go";
  if (/\bfunc\s+\w+/.test(source) && (/->/.test(source) || /\b(?:let|guard|var)\s+/.test(source))) return "swift";
  if (/^\s*object\s+\w+/m.test(source) && /\bdef\s+\w+/.test(source)) return "scala";
  if (/^\s*(?:async\s+)?def\s+\w+.*:\s*(?:#.*)?$/m.test(source) || /\bself\b/.test(source)) return "python";
  if (/^\s*def\s+\w+/m.test(source) && /^\s*end\s*$/m.test(source)) return "ruby";
  if (/^\s*(?:local\s+)?function\b/m.test(source) && /^\s*end\s*$/m.test(source)) return "lua";
  if (/\bnamespace\b|\bConsole\.(?:Write|Read)/.test(source)) return "csharp";
  if (/\b(?:public|private|protected)\s+(?:static\s+)?(?:class|void|int|boolean|String|long)\b|\bSystem\.out\b/.test(source)) return "java";
  if (source.includes("#include") && (source.includes("std::") || source.includes("cout") || source.includes("template"))) return "cpp";
  if (source.includes("#include") || /\bint\s+main\s*\(/.test(source)) return "c";
  if (/\binterface\s+\w+|\btype\s+\w+\s*=|:\s*(?:string|number|boolean)\b/.test(source)) return "typescript";
  if (/\bfunction\b|=>|\bconsole\.|\bconst\b|\blet\b/.test(source)) return "javascript";
  if (/\$\w+/.test(source) && /\bfunction\b/.test(source)) return "php";
  return (source.split("{").length >= source.split(":\n").length) ? "c" : "python";
}

function mask(source) {
  let out = "";
  let i = 0;
  while (i < source.length) {
    const ch = source[i];
    const nxt = source[i + 1] || "";
    if (ch === "'" || ch === '"' || ch === "`") {
      const token = source.slice(i, i + 3) === ch.repeat(3) ? ch.repeat(3) : ch;
      out += " ".repeat(token.length);
      i += token.length;
      while (i < source.length) {
        if (source[i] === "\\") {
          out += "  ";
          i += 2;
          continue;
        }
        if (source.startsWith(token, i)) {
          out += " ".repeat(token.length);
          i += token.length;
          break;
        }
        out += source[i] === "\n" ? "\n" : " ";
        i += 1;
      }
      continue;
    }
    if (ch === "#" || (ch === "/" && nxt === "/")) {
      const step = ch === "#" ? 1 : 2;
      out += " ".repeat(step);
      i += step;
      while (i < source.length && source[i] !== "\n") {
        out += " ";
        i += 1;
      }
      continue;
    }
    if (ch === "/" && nxt === "*") {
      out += "  ";
      i += 2;
      while (i < source.length && !(source[i] === "*" && source[i + 1] === "/")) {
        out += source[i] === "\n" ? "\n" : " ";
        i += 1;
      }
      out += "  ";
      i += 2;
      continue;
    }
    out += ch;
    i += 1;
  }
  return out;
}

function bodiesOf(code, language) {
  const matches = [];
  DEF.lastIndex = 0;
  let match;
  while ((match = DEF.exec(code))) {
    matches.push({ name: match[1], end: match.index + match[0].length, start: match.index });
  }
  if (C_LANGS.has(language)) {
    CDEF.lastIndex = 0;
    while ((match = CDEF.exec(code))) {
      if (!SKIP.has(match[1])) matches.push({ name: match[1], end: match.index + match[0].length, start: match.index });
    }
  }
  matches.sort((a, b) => a.start - b.start);
  return matches.map((item, index) => {
    const end = index + 1 < matches.length ? matches[index + 1].start : code.length;
    return [item.name, code.slice(item.end, end)];
  });
}

function classify(body, name, language) {
  const [nest, product, sort] = measure(body, language);
  const calls = name ? (body.match(new RegExp(`\\b${name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*\\(`, "g")) || []).length : 0;
  const logarithmic = LOG.test(body) && !/ for /.test(` ${body} `);
  let time = "O(1)";
  let reason = "no loop";
  if (calls >= 2 && logarithmic) {
    time = "O(n log n)";
    reason = "2 recursive calls";
  } else if (calls >= 2) {
    time = "O(c^n)";
    reason = "2 recursive calls";
  } else if (calls === 1 && logarithmic && nest === 0) {
    time = "O(log n)";
    reason = "1 recursive call";
  } else if (calls === 1 && nest === 0) {
    time = "O(n)";
    reason = "1 recursive call";
  } else if (product && nest > 3) {
    time = "O(n^k)";
    reason = "matrix product inside a loop";
  } else if (product) {
    time = "O(n^3)";
    reason = "matrix product";
  } else if (sort && nest === 0) {
    time = "O(n log n)";
    reason = "sort";
  } else if (sort) {
    time = "O(n^k)";
    reason = "sort inside a loop";
  } else if (nest === 0 && logarithmic) {
    time = "O(log n)";
    reason = "halves the range";
  } else if (nest <= 0) {
    time = "O(1)";
    reason = "no loop";
  } else if (nest === 1 && logarithmic) {
    time = "O(log n)";
    reason = "halves the range";
  } else if (nest === 1) {
    time = "O(n)";
    reason = "1 loop";
  } else if (nest === 2) {
    time = "O(n^2)";
    reason = "2 nested loops";
  } else if (nest === 3) {
    time = "O(n^3)";
    reason = "3 nested loops";
  } else {
    time = "O(n^k)";
    reason = `${nest} nested loops`;
  }

  const spaces = ["O(1)"];
  if (calls >= 1 && logarithmic) spaces.push("O(log n)");
  else if (calls >= 1) spaces.push("O(n)");
  if (product) spaces.push("O(n^2)");
  if (sort) spaces.push("O(n)");
  if (GROW.test(body) && nest >= 1) spaces.push({ 1: "O(n)", 2: "O(n^2)", 3: "O(n^3)" }[nest] || "O(n^k)");
  const space = spaces.reduce((best, item) => (RANK.indexOf(item) > RANK.indexOf(best) ? item : best));
  return [time, space, reason];
}

function measure(body, language) {
  const indent = measureIndent(body);
  const braces = measureBraces(body);
  if (INDENT_LANGS.has(language)) {
    return [Math.max(indent[0], braces[0]), indent[1] || braces[1], indent[2] || braces[2]];
  }
  return braces;
}

function lineFacts(stripped) {
  const header = HEADER.test(stripped);
  const product = LINALG.test(stripped) || matmul(stripped);
  const sort = SORT.test(stripped);
  const scan = !header && SCAN.test(stripped);
  return [header, product, sort, scan];
}

function matmul(stripped) {
  if (stripped.startsWith("@")) return false;
  return stripped.includes("@");
}

function expandTabs(line) {
  let out = "";
  let col = 0;
  for (const ch of line) {
    if (ch === "\t") {
      const size = 4 - (col % 4);
      out += " ".repeat(size);
      col += size;
    } else {
      out += ch;
      col += 1;
    }
  }
  return out;
}

function measureIndent(body) {
  const stack = [];
  let best = 0;
  let product = false;
  let sort = false;
  for (const raw of body.split("\n")) {
    const expanded = expandTabs(raw);
    if (!expanded.trim()) continue;
    let indent = 0;
    while (expanded[indent] === " ") indent += 1;
    const stripped = expanded.slice(indent);
    while (stack.length && indent <= stack[stack.length - 1]) stack.pop();
    const [header, lineProduct, lineSort, scan] = lineFacts(stripped);
    product = product || lineProduct;
    sort = sort || lineSort;
    const loops = (stripped.match(LOOP_WORDS) || []).length;
    if (header && WORD_LOOP.test(stripped)) {
      stack.push(indent);
      best = Math.max(best, stack.length + Math.max(loops - 1, 0));
    } else if (header) {
      stack.push(indent);
      best = Math.max(best, stack.length + Math.max(loops, 0));
    } else if (loops) {
      best = Math.max(best, stack.length + loops);
    }
    if (lineProduct) best = Math.max(best, stack.length + 3);
    else if (scan) best = Math.max(best, stack.length + 1);
  }
  return [best, product, sort];
}

function measureBraces(body) {
  let depth = 0;
  const loops = [];
  let pending = false;
  let best = 0;
  let product = false;
  let sort = false;
  for (let i = 0; i < body.length;) {
    const found = PENDING.exec(body.slice(i));
    if (found) {
      pending = true;
      i += found[0].length;
      continue;
    }
    const ch = body[i];
    if (ch === "\n") {
      const start = body.lastIndexOf("\n", i - 1);
      const line = body.slice(start + 1, i);
      const [, lineProduct, lineSort, scan] = lineFacts(line.trim());
      product = product || lineProduct;
      sort = sort || lineSort;
      if (lineProduct) best = Math.max(best, loops.length + 3);
      else if (scan) best = Math.max(best, loops.length + 1);
    }
    if (ch === "{") {
      depth += 1;
      if (pending) {
        loops.push(depth);
        pending = false;
        best = Math.max(best, loops.length);
      }
    } else if (ch === "}") {
      if (loops.length && loops[loops.length - 1] === depth) loops.pop();
      depth = Math.max(0, depth - 1);
      pending = false;
    } else if (ch === ";" && pending) {
      best = Math.max(best, loops.length + 1);
      pending = false;
    }
    i += 1;
  }
  const tail = body.slice(body.lastIndexOf("\n") + 1);
  const [, lineProduct, lineSort, scan] = lineFacts(tail.trim());
  product = product || lineProduct;
  sort = sort || lineSort;
  if (lineProduct) best = Math.max(best, loops.length + 3);
  else if (scan) best = Math.max(best, loops.length + 1);
  return [best, product, sort];
}

globalThis.analyzeSource = analyzeSource;
