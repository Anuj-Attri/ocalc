const samples = {
  python: `def pairs(rows):
    count = 0
    for row in rows:
        for value in row:
            count += 1
    return count
`,
  javascript: `function sum(items) {
  let total = 0;
  for (let i = 0; i < items.length; i++) {
    total += items[i];
  }
  return total;
}
`,
  go: `func sum(nums []int) int {
  total := 0
  for i := 0; i < len(nums); i++ {
    total += nums[i]
  }
  return total
}
`,
  search: `def search(nums, target):
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
};

const code = document.querySelector("#code");
const file = document.querySelector("#file");
const language = document.querySelector("#language");
const time = document.querySelector("#time");
const space = document.querySelector("#space");
const detail = document.querySelector("#detail");

function render() {
  const result = analyzeSource(code.value);
  language.textContent = result.language;
  time.textContent = result.time;
  space.textContent = result.space;
  detail.textContent = result.detail;
}

code.addEventListener("input", render);

file.addEventListener("change", () => {
  const chosen = file.files && file.files[0];
  if (!chosen) return;
  const reader = new FileReader();
  reader.onload = () => {
    code.value = String(reader.result || "");
    render();
  };
  reader.readAsText(chosen);
});

document.querySelectorAll("[data-sample]").forEach((button) => {
  button.addEventListener("click", () => {
    code.value = samples[button.dataset.sample];
    render();
  });
});

render();
