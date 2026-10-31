import {
  EditorState,
  EditorView,
  Prec,
  Compartment,
  keymap,
  lineNumbers,
  drawSelection,
  highlightActiveLine,
  defaultKeymap,
  history,
  historyKeymap,
  indentWithTab,
  indentUnit,
  indentService,
  bracketMatching,
  syntaxHighlighting,
  defaultHighlightStyle,
  indentOnInput,
  closeBrackets,
  closeBracketsKeymap,
  python,
  javascript,
  go,
  rust,
  java,
  cpp,
  cMode,
  php,
  StreamLanguage,
  ruby,
  swift,
  lua,
  kotlin,
  csharp,
  scala,
} from "./cm.js";

const examples = [
  {
    id: "gemm",
    label: "Python · two functions",
    language: "python",
    code: `import numpy as np

def scale(items):
    return [2 * item for item in items]

def gemm(x: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Multiply x and w."""
    return x @ w
`,
  },
  {
    id: "pairs",
    label: "Python · nested loops",
    language: "python",
    code: `def pairs(rows):
    count = 0
    for row in rows:
        for value in row:
            count += 1
    return count
`,
  },
  {
    id: "search",
    label: "Python · binary search",
    language: "python",
    code: `def search(nums, target):
    low = 0
    high = len(nums) - 1
    while low <= high:
        mid = (low + high) // 2
        if nums[mid] == target:
            return mid
        if nums[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
`,
  },
  {
    id: "javascript",
    label: "JavaScript",
    language: "javascript",
    code: `function sum(items) {
    let total = 0;
    items.forEach((item) => {
        total += item;
    });
    return total;
}
`,
  },
  {
    id: "typescript",
    label: "TypeScript",
    language: "typescript",
    code: `function sum(items: number[]): number {
    let total = 0;
    for (const n of items) {
        total += n;
    }
    return total;
}
`,
  },
  {
    id: "go",
    label: "Go",
    language: "go",
    code: `func sum(nums []int) int {
	total := 0
	for i := 0; i < len(nums); i++ {
		total += nums[i]
	}
	return total
}
`,
  },
  {
    id: "rust",
    label: "Rust",
    language: "rust",
    code: `fn sum(nums: &[i32]) -> i32 {
    let mut total = 0;
    for n in nums {
        total += n;
    }
    total
}
`,
  },
  {
    id: "java",
    label: "Java",
    language: "java",
    code: `class T {
    public int sum(int[] items) {
        int total = 0;
        for (int i = 0; i < items.length; i++) {
            total += items[i];
        }
        return total;
    }
}
`,
  },
  {
    id: "c",
    label: "C",
    language: "c",
    code: `#include <stdio.h>

int sum(int *nums, int n) {
    int total = 0;
    for (int i = 0; i < n; i++) {
        total += nums[i];
    }
    return total;
}
`,
  },
  {
    id: "cpp",
    label: "C++",
    language: "cpp",
    code: `#include <vector>

int sum(const std::vector<int>& nums) {
    int total = 0;
    for (int n : nums) {
        total += n;
    }
    return total;
}
`,
  },
  {
    id: "csharp",
    label: "C#",
    language: "csharp",
    code: `namespace T {
    public int Sum(int[] items) {
        int total = 0;
        foreach (var n in items) {
            total += n;
        }
        return total;
    }
}
`,
  },
  {
    id: "ruby",
    label: "Ruby",
    language: "ruby",
    code: `def pairs(rows)
  rows.each do |row|
    row.each do |value|
      value
    end
  end
end
`,
  },
  {
    id: "php",
    label: "PHP",
    language: "php",
    code: `<?php
function sum($nums) {
    $total = 0;
    foreach ($nums as $n) {
        $total += $n;
    }
    return $total;
}
`,
  },
  {
    id: "kotlin",
    label: "Kotlin",
    language: "kotlin",
    code: `fun sum(nums: List<Int>): Int {
    var total = 0
    for (n in nums) {
        total += n
    }
    return total
}
`,
  },
  {
    id: "swift",
    label: "Swift",
    language: "swift",
    code: `func sum(nums: [Int]) -> Int {
    var total = 0
    for n in nums {
        total += n
    }
    return total
}
`,
  },
  {
    id: "lua",
    label: "Lua",
    language: "lua",
    code: `function sum(nums)
    local total = 0
    for _, n in ipairs(nums) do
        total = total + n
    end
    return total
end
`,
  },
];

const extensions = {
  py: "python", js: "javascript", jsx: "javascript", mjs: "javascript",
  ts: "typescript", tsx: "typescript", go: "go", rs: "rust", java: "java",
  c: "c", h: "c", cpp: "cpp", cc: "cpp", cxx: "cpp", hpp: "cpp", hh: "cpp",
  cs: "csharp", rb: "ruby", php: "php", kt: "kotlin", kts: "kotlin",
  swift: "swift", scala: "scala", sc: "scala", lua: "lua",
};

const languageSelect = document.querySelector("#language");
const exampleSelect = document.querySelector("#example");
const fileInput = document.querySelector("#file");
const timeNode = document.querySelector("#time");
const spaceNode = document.querySelector("#space");
const timeMeta = document.querySelector("#time-meta");
const spaceMeta = document.querySelector("#space-meta");
const rows = document.querySelector("#rows");
const cursor = document.querySelector("#cursor");
const detected = document.querySelector("#detected");
const boot = document.querySelector("#boot");

const languageConf = new Compartment();
const indentConf = new Compartment();
let activeLanguage = "";

function modeFor(language) {
  switch (language) {
    case "python": return python();
    case "javascript": return javascript();
    case "typescript": return javascript({ typescript: true });
    case "go": return go();
    case "rust": return rust();
    case "java": return java();
    case "c": return StreamLanguage.define(cMode);
    case "cpp": return cpp();
    case "php": return php();
    case "ruby": return StreamLanguage.define(ruby);
    case "swift": return StreamLanguage.define(swift);
    case "lua": return StreamLanguage.define(lua);
    case "kotlin": return StreamLanguage.define(kotlin);
    case "csharp": return StreamLanguage.define(csharp);
    case "scala": return StreamLanguage.define(scala);
    default: return [];
  }
}

function unitFor(language) {
  return language === "go" ? "\t" : "    ";
}

function copyIndent(context, pos) {
  const line = context.lineAt(pos);
  if (line.from === 0) return 0;
  const prev = context.state.doc.lineAt(line.from - 1);
  const leading = /^[ \t]*/.exec(prev.text)[0];
  let col = 0;
  for (const ch of leading) col += ch === "\t" ? context.unit : 1;
  if (/[:{]\s*(?:\/\/.*|#.*)?$/.test(prev.text) || /\b(?:do|then)\s*$/.test(prev.text.trim())) {
    col += context.unit;
  }
  return col;
}

function worstNamed(result, field) {
  return result.functions.reduce((best, item) => (
    rankOf(item[field]) > rankOf(best[field]) ? item : best
  ));
}

function rankOf(label) {
  return ["O(1)", "O(log n)", "O(n)", "O(n log n)", "O(n^2)", "O(n^3)", "O(n^k)", "O(c^n)"].indexOf(label);
}

function paint(view) {
  const chosen = languageSelect.value;
  const text = view.state.doc.toString();
  const result = globalThis.analyzeSource(text, chosen === "auto" ? undefined : chosen);
  const shown = chosen === "auto" ? result.language : chosen;
  const head = view.state.selection.main.head;
  const line = view.state.doc.lineAt(head);
  const timeFn = worstNamed(result, "time");
  const spaceFn = worstNamed(result, "space");
  cursor.textContent = `Ln ${line.number}, Col ${head - line.from + 1}`;
  const option = [...languageSelect.options].find((item) => item.value === shown);
  detected.textContent = option ? option.textContent : shown;
  timeNode.textContent = result.time;
  spaceNode.textContent = result.space;
  timeMeta.textContent = `${timeFn.name} · ${timeFn.reason}`;
  spaceMeta.textContent = spaceFn.name === timeFn.name ? timeFn.name : spaceFn.name;
  rows.replaceChildren(...result.functions.map((fn) => {
    const tr = document.createElement("tr");
    if (fn.name === timeFn.name && fn.time === result.time) tr.className = "worst";
    for (const [textValue, className] of [[fn.name, ""], [fn.time, ""], [fn.space, ""], [fn.reason, "why"]]) {
      const td = document.createElement("td");
      if (className) td.className = className;
      td.textContent = textValue;
      tr.append(td);
    }
    return tr;
  }));
  if (shown !== activeLanguage) {
    const target = shown;
    queueMicrotask(() => {
      if (target === activeLanguage) return;
      activeLanguage = target;
      view.dispatch({
        effects: [
          languageConf.reconfigure(modeFor(target)),
          indentConf.reconfigure(indentUnit.of(unitFor(target))),
        ],
      });
    });
  }
}

const first = examples[0];
const custom = document.createElement("option");
custom.value = "";
custom.textContent = "Custom";
custom.hidden = true;
exampleSelect.append(custom);
for (const example of examples) {
  const option = document.createElement("option");
  option.value = example.id;
  option.textContent = example.label;
  exampleSelect.append(option);
}
exampleSelect.value = first.id;

const view = new EditorView({
  parent: document.querySelector("#editor"),
  state: EditorState.create({
    doc: first.code,
    extensions: [
      lineNumbers(),
      drawSelection(),
      highlightActiveLine(),
      history(),
      indentOnInput(),
      bracketMatching(),
      closeBrackets(),
      syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
      keymap.of([...closeBracketsKeymap, ...defaultKeymap, ...historyKeymap]),
      Prec.highest(keymap.of([indentWithTab])),
      Prec.lowest(indentService.of(copyIndent)),
      languageConf.of(modeFor(first.language)),
      indentConf.of(indentUnit.of(unitFor(first.language))),
      EditorState.tabSize.of(4),
      EditorView.theme({
        "&": { height: "100%" },
      }),
      EditorView.updateListener.of((update) => {
        if (update.docChanged || update.selectionSet) paint(update.view);
      }),
    ],
  }),
});

activeLanguage = first.language;
paint(view);
boot.remove();

languageSelect.addEventListener("change", () => paint(view));

exampleSelect.addEventListener("change", () => {
  const example = examples.find((item) => item.id === exampleSelect.value);
  if (!example) return;
  languageSelect.value = example.language;
  view.dispatch({
    changes: { from: 0, to: view.state.doc.length, insert: example.code },
    selection: { anchor: 0 },
  });
  paint(view);
});

fileInput.addEventListener("change", () => {
  const chosen = fileInput.files && fileInput.files[0];
  if (!chosen) return;
  const reader = new FileReader();
  reader.onload = () => {
    const text = String(reader.result || "");
    const ext = (chosen.name.split(".").pop() || "").toLowerCase();
    languageSelect.value = extensions[ext] || "auto";
    exampleSelect.value = "";
    view.dispatch({
      changes: { from: 0, to: view.state.doc.length, insert: text },
      selection: { anchor: 0 },
    });
    paint(view);
  };
  reader.readAsText(chosen);
});
