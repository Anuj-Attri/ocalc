const RANK = ["O(1)", "O(log n)", "O(n)", "O(n log n)", "O(n^2)", "O(n^3)", "O(n^k)", "O(c^n)"];

function analyzeSource(source, language) {
  language = (language || detect(source)).toLowerCase();
  const code = mask(source);
  let bodies = bodiesOf(code, language);
  if (!bodies.length) bodies = [["", code]];
  let bestTime = "O(1)";
  let bestSpace = "O(1)";
  for (const [name, body] of bodies) {
    const result = classify(body, name, language);
    if (RANK.indexOf(result.time) > RANK.indexOf(bestTime)) bestTime = result.time;
    if (RANK.indexOf(result.space) > RANK.indexOf(bestSpace)) bestSpace = result.space;
  }
  const detail = bodies.length + " function" + (bodies.length === 1 ? "" : "s");
  return { language, time: bestTime, space: bestSpace, detail };
}

function detect(source) {
  if (/^\s*def\s+\w+\s*\(/m.test(source) || /\bself\b/.test(source)) return "python";
  if (/\bpackage\s+main\b|\bfunc\s+/.test(source)) return "go";
  if (/\bfn\s+\w+\s*\(/.test(source)) return "rust";
  if (/#include\b|\bint\s+main\s*\(/.test(source)) return "c";
  if (/\bpublic\s+class\b|\bSystem\.out\b/.test(source)) return "java";
  if (/\bfunction\b|=>|\bconsole\.|\bconst\b|\blet\b/.test(source)) return "javascript";
  return (source.split("{").length >= source.split(":\n").length) ? "c" : "python";
}

function mask(source) {
  let out = "";
  let i = 0;
  while (i < source.length) {
    const ch = source[i];
    const nxt = source[i + 1] || "";
    if (ch === "'" || ch === '"' || ch === "`") {
      const quote = ch;
      out += " ";
      i += 1;
      while (i < source.length) {
        if (source[i] === "\\") {
          out += "  ";
          i += 2;
          continue;
        }
        if (source[i] === quote) {
          out += " ";
          i += 1;
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
  const defRe = /\b(?:def|function|func|fn|fun)\s+([A-Za-z_]\w*)\s*\(/g;
  let match;
  while ((match = defRe.exec(code))) matches.push({ name: match[1], end: match.index + match[0].length, start: match.index });
  if (["c", "java", "cpp", "csharp"].includes(language)) {
    const cRe = /^[ \t]*(?:(?:public|private|protected|static|async|inline|virtual|const)\s+)*(?:[\w:<>,*&[\]]+\s+)+([A-Za-z_]\w*)\s*\([^;]*\)\s*\{/gm;
    const skip = new Set(["if", "for", "while", "switch", "catch", "return", "sizeof"]);
    while ((match = cRe.exec(code))) {
      if (!skip.has(match[1])) matches.push({ name: match[1], end: match.index + match[0].length, start: match.index });
    }
  }
  matches.sort((a, b) => a.start - b.start);
  return matches.map((item, index) => {
    const end = index + 1 < matches.length ? matches[index + 1].start : code.length;
    return [item.name, code.slice(item.end, end)];
  });
}

function classify(body, name, language) {
  const nest = nesting(body, language);
  const calls = name ? (body.match(new RegExp("\\b" + name + "\\s*\\(", "g")) || []).length : 0;
  const logarithmic = /while\s+.*\b(?:low|left|lo|start)\s*<=?\s*(?:high|right|hi|end)\b|\/=\s*2|\/\/=\s*2|>>=\s*1|=\s*\w+\s*\/\s*2|=\s*\w+\s*\/\/\s*2/.test(body)
    && !/ for /.test(" " + body + " ");
  let time = "O(1)";
  if (calls >= 2 && logarithmic) time = "O(n log n)";
  else if (calls >= 2) time = "O(c^n)";
  else if (calls === 1 && logarithmic && nest === 0) time = "O(log n)";
  else if (calls === 1 && nest === 0) time = "O(n)";
  else if (nest === 0 && logarithmic) time = "O(log n)";
  else if (nest <= 0) time = "O(1)";
  else if (nest === 1 && logarithmic) time = "O(log n)";
  else if (nest === 1) time = "O(n)";
  else if (nest === 2) time = "O(n^2)";
  else if (nest === 3) time = "O(n^3)";
  else time = "O(n^k)";

  let space = "O(1)";
  if (calls >= 1 && logarithmic) space = "O(log n)";
  else if (calls >= 1) space = "O(n)";
  else if (/\b(?:append|push|push_back|emplace|emplace_back|add)\s*\(|\bnew\s+\w+\s*\[/.test(body) && nest >= 1) {
    space = { 1: "O(n)", 2: "O(n^2)", 3: "O(n^3)" }[nest] || "O(n^k)";
  }
  return { time, space };
}

function nesting(body, language) {
  if (language === "python") return nestIndent(body);
  return Math.max(nestBraces(body), language === "ruby" ? nestIndent(body) : 0);
}

function nestIndent(body) {
  const stack = [];
  let best = 0;
  for (const line of body.split("\n")) {
    if (!line.trim()) continue;
    const indent = line.length - line.trimStart().length;
    while (stack.length && indent <= stack[stack.length - 1]) stack.pop();
    const stripped = line.trim();
    let loops = (stripped.match(/\b(?:for|while)\b/g) || []).length;
    if (/^(?:for|while|async\s+for)\b/.test(stripped)) {
      stack.push(indent);
      loops -= 1;
      best = Math.max(best, stack.length + Math.max(loops, 0));
    } else if (loops) {
      best = Math.max(best, stack.length + loops);
    }
  }
  return best;
}

function nestBraces(body) {
  let depth = 0;
  const loops = [];
  let pending = false;
  let best = 0;
  for (let i = 0; i < body.length; i += 1) {
    if (/^(?:for|while|loop)\b/.test(body.slice(i))) {
      pending = true;
      i += 1;
      continue;
    }
    const ch = body[i];
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
  }
  return best;
}
