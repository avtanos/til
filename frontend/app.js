const $ = (id) => document.getElementById(id);

const examples = {
  min: `башкы() {
    бүтүн n = окуу();
    чыгар(n);
}`,
  cmp: `башкы() {
    бүтүн a = окуу();
    бүтүн b = окуу();
    эгер (a > b) {
        чыгар("чоң");
    } болбосо {
        чыгар("кичине");
    }
}`,
  sum: `башкы() {
    бүтүн n = окуу();
    бүтүн s = 0;
    үчүн (бүтүн i = 0; i < n; i = i + 1) {
        s = s + (i + 1);
    }
    чыгар(s);
}`,

  fact: `функция факт(бүтүн n) {
    эгер (n <= 1) {
        кайтар 1;
    } болбосо {
        кайтар n * факт(n - 1);
    }
}

башкы() {
    бүтүн n = окуу();
    чыгар(факт(n));
}`,

  while: `башкы() {
    бүтүн n = окуу();
    качан (n > 0) {
        чыгар(n);
        n = n - 1;
    }
}`,

  dowhile: `башкы() {
    бүтүн n = окуу();
    бүтүн i = 0;
    жаса {
        чыгар(i);
        i = i + 1;
    } качан (i < n);
}`,

  logic: `башкы() {
    бүтүн a = окуу();
    бүтүн b = окуу();
    эгер ((a > b) жана (b > 0)) {
        чыгар("туура");
    } болбосо {
        эгер (эмес (a > b)) {
            чыгар("күтө тур");
        } болбосо {
            чыгар("калп");
        }
    }
}`,

  arrsum: `башкы() {
    бүтүн n = окуу();
    тизме<бүтүн> a = [10, 20, 30, 40, 50];
    бүтүн s = 0;
    үчүн (бүтүн i = 0; i < n; i = i + 1) {
        эгер (i >= узундук(a)) {
            токтот;
        }
        s = s + a[i];
    }
    чыгар(s);
}`,

  strlen: `башкы() {
    сап t = окуу();
    чыгар(узундук(t));
}`,

  cont: `башкы() {
    бүтүн n = окуу();
    бүтүн s = 0;
    үчүн (бүтүн i = 0; i < n; i = i + 1) {
        эгер (i % 2 == 0) {
            улантуу;
        }
        s = s + i;
        эгер (s > 1000) {
            токтот;
        }
    }
    чыгар(s);
}`,
};

function setExample(name) {
  $("code").value = examples[name] ?? "";
  scheduleHighlight(true);
  scheduleSyntaxCheck();
}

function formatCode() {
  const textarea = $("code");
  if (!textarea) return;

  const src = textarea.value ?? "";
  const normalized = src.replace(/\r\n?/g, "\n").replace(/\t/g, "    ");
  const lines = normalized.split("\n");

  const INDENT = 2; // spaces per indent level
  let indent = 0;
  const out = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmedRight = line.replace(/\s+$/g, "");
    const trimmed = trimmedRight.trim();

    if (!trimmed) {
      out.push("");
      continue;
    }

    // Keep trailing comments (// ...) intact.
    // Note: assumes comments don't contain string literals with `//`.
    const commentIdx = trimmed.indexOf("//");
    const codePart = commentIdx >= 0 ? trimmed.slice(0, commentIdx).trimEnd() : trimmed;
    const commentPart = commentIdx >= 0 ? trimmed.slice(commentIdx).trimEnd() : "";

    const closeLeadingMatch = codePart.match(/^}+/);
    const closeLeading = closeLeadingMatch ? closeLeadingMatch[0].length : 0;

    indent = Math.max(0, indent - closeLeading);

    const openTotal = (codePart.match(/{/g) || []).length;
    const closeTotal = (codePart.match(/}/g) || []).length;
    const closeRest = Math.max(0, closeTotal - closeLeading);

    const indentStr = " ".repeat(indent * INDENT);
    const formattedLine = indentStr + codePart + (commentPart ? ` ${commentPart}` : "");
    out.push(formattedLine);

    // Indentation for subsequent lines: add for opens, subtract for closings after the line start.
    indent = indent + openTotal - closeRest;
  }

  // Avoid extra newline at the end (Textarea will display it anyway if user needs).
  textarea.value = out.join("\n").replace(/\s+$/g, "");
  scheduleHighlight(true);
  scheduleSyntaxCheck();
}

// -----------------------------
// Sublime-like editor features:
// - auto syntax highlight on typing
// - auto indent on Enter and for lines starting with '}'
// - colored tokens for language keywords/operators/symbols
// -----------------------------

const INDENT_UNIT = 2;

const TIL_KEYWORDS = new Set([
  "функция",
  "эгер",
  "болбосо",
  "качан",
  "жаса",
  "үчүн",
  "токтот",
  "улантуу",
  "кайтар",
  "жана",
  "же",
  "эмес",
]);

const TIL_TYPES = new Set(["бүтүн", "чыныгы", "сап", "белги", "логикалык", "тизме"]);
const TIL_BUILTINS = new Set(["окуу", "чыгар", "узундук"]);
const TIL_BOOLEANS = new Set(["чын", "жалган"]);
const TIL_MAIN_FN = "башкы";

const OP2 = new Set(["&&", "||", "==", "!=", ">=", "<="]);
const OP1 = new Set(["+", "-", "*", "/", "%", "=", "!", ">", "<"]);
const PUNCT = new Set(["{", "}", "(", ")", "[", "]", ",", ";", ".", "<", ">", ":"]);

const WORD_CHAR_RE = /[\p{L}\p{M}\p{N}_]/u;

function escapeHtml(s) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function wrapTok(cls, text) {
  return `<span class="${cls}">${escapeHtml(text)}</span>`;
}

function tokenizeToHtml(code) {
  let out = "";
  let i = 0;
  const len = code.length;

  while (i < len) {
    const ch = code[i];

    // Line comment //
    if (ch === "/" && code[i + 1] === "/") {
      let j = i + 2;
      while (j < len && code[j] !== "\n") j++;
      out += wrapTok("tok-comment", code.slice(i, j));
      i = j;
      continue;
    }

    // Block comment /* ... */
    if (ch === "/" && code[i + 1] === "*") {
      let j = i + 2;
      while (j < len) {
        if (code[j] === "*" && code[j + 1] === "/") {
          j += 2;
          break;
        }
        j++;
      }
      out += wrapTok("tok-comment", code.slice(i, j));
      i = j;
      continue;
    }

    // String literal "..."
    if (ch === '"') {
      let j = i + 1;
      while (j < len) {
        if (code[j] === '"' && code[j - 1] !== "\\") {
          j++;
          break;
        }
        // MVP lexer forbids newline in literals, but we still keep highlighting stable.
        if (code[j] === "\n") break;
        j++;
      }
      out += wrapTok("tok-str", code.slice(i, j));
      i = j;
      continue;
    }

    // Char literal 'a'
    if (ch === "'") {
      let j = i + 1;
      while (j < len) {
        if (code[j] === "'" && code[j - 1] !== "\\") {
          j++;
          break;
        }
        if (code[j] === "\n") break;
        j++;
      }
      out += wrapTok("tok-str", code.slice(i, j));
      i = j;
      continue;
    }

    // Multi-char operators
    const two = code.slice(i, i + 2);
    if (OP2.has(two)) {
      out += wrapTok("tok-op", two);
      i += 2;
      continue;
    }

    // Numbers
    if (ch >= "0" && ch <= "9") {
      let j = i + 1;
      while (j < len && code[j] >= "0" && code[j] <= "9") j++;
      if (code[j] === "." && j + 1 < len && code[j + 1] >= "0" && code[j + 1] <= "9") {
        j++;
        while (j < len && code[j] >= "0" && code[j] <= "9") j++;
      }
      out += wrapTok("tok-num", code.slice(i, j));
      i = j;
      continue;
    }

    // Words / identifiers / keywords
    if (WORD_CHAR_RE.test(ch)) {
      let j = i + 1;
      while (j < len && WORD_CHAR_RE.test(code[j])) j++;
      const word = code.slice(i, j);

      if (TIL_TYPES.has(word)) out += wrapTok("tok-type", word);
      else if (TIL_KEYWORDS.has(word)) out += wrapTok("tok-kw", word);
      else if (TIL_BOOLEANS.has(word)) out += wrapTok("tok-bool", word);
      else if (word === TIL_MAIN_FN || TIL_BUILTINS.has(word)) out += wrapTok("tok-fn", word);
      else out += escapeHtml(word);

      i = j;
      continue;
    }

    // Single-char operators
    if (OP1.has(ch)) {
      out += wrapTok("tok-op", ch);
      i++;
      continue;
    }

    // Punctuation/symbols
    if (PUNCT.has(ch)) {
      out += wrapTok("tok-punct", ch);
      i++;
      continue;
    }

    out += escapeHtml(ch);
    i++;
  }

  return out;
}

function braceLevelUpTo(text, index) {
  // Counts `{` and `}` outside of strings/comments.
  let level = 0;
  let inLineComment = false;
  let inBlockComment = false;
  let inDouble = false;
  let inSingle = false;

  for (let i = 0; i < index; i++) {
    const ch = text[i];
    const next = text[i + 1];

    if (inLineComment) {
      if (ch === "\n") inLineComment = false;
      continue;
    }

    if (inBlockComment) {
      if (ch === "*" && next === "/") {
        inBlockComment = false;
        i++; // consume '/'
      }
      continue;
    }

    if (inDouble) {
      if (ch === '"' && text[i - 1] !== "\\") inDouble = false;
      continue;
    }

    if (inSingle) {
      if (ch === "'" && text[i - 1] !== "\\") inSingle = false;
      continue;
    }

    // Enter comment
    if (ch === "/" && next === "/") {
      inLineComment = true;
      i++; // consume second '/'
      continue;
    }

    if (ch === "/" && next === "*") {
      inBlockComment = true;
      i++; // consume '*'
      continue;
    }

    // Enter strings/chars
    if (ch === '"') {
      inDouble = true;
      continue;
    }
    if (ch === "'") {
      inSingle = true;
      continue;
    }

    if (ch === "{") level++;
    else if (ch === "}") level = Math.max(0, level - 1);
  }

  return level;
}

function reindentCurrentLine() {
  const ta = $("code");
  if (!ta) return;
  const value = ta.value ?? "";

  const pos = ta.selectionStart ?? 0;
  const lineStart = value.lastIndexOf("\n", Math.max(0, pos - 1)) + 1;
  let lineEnd = value.indexOf("\n", pos);
  if (lineEnd < 0) lineEnd = value.length;

  const line = value.slice(lineStart, lineEnd);
  const oldIndentMatch = line.match(/^\s*/);
  const oldIndentLen = oldIndentMatch ? oldIndentMatch[0].length : 0;
  const trimmedStart = line.trimStart();

  const baseLevel = braceLevelUpTo(value, lineStart);
  const desiredLevel = trimmedStart.startsWith("}") ? Math.max(0, baseLevel - 1) : baseLevel;
  const indentStr = " ".repeat(desiredLevel * INDENT_UNIT);
  const newLine = indentStr + trimmedStart;

  if (newLine === line) return;

  const newValue = value.slice(0, lineStart) + newLine + value.slice(lineEnd);
  const caretDelta = indentStr.length - oldIndentLen;
  ta.value = newValue;
  ta.selectionStart = pos + caretDelta;
  ta.selectionEnd = pos + caretDelta;
}

let highlightTimer = null;
function scheduleHighlight(immediate = false) {
  const ta = $("code");
  const pre = $("codeHighlight");
  if (!ta || !pre) return;
  if (highlightTimer) clearTimeout(highlightTimer);

  const run = () => {
    pre.innerHTML = tokenizeToHtml(ta.value ?? "");
    pre.scrollTop = ta.scrollTop;
    pre.scrollLeft = ta.scrollLeft;
  };

  if (immediate) run();
  else highlightTimer = setTimeout(run, 50);
}

let lastKeyWasBrace = false;
let isApplyingReindent = false;

let syntaxDebounceTimer = null;
function scheduleSyntaxCheck() {
  if (syntaxDebounceTimer) clearTimeout(syntaxDebounceTimer);
  syntaxDebounceTimer = setTimeout(() => {
    checkSyntax().catch(() => {
      /* ignore */
    });
  }, 650);
}

function installCodeEditor() {
  const ta = $("code");
  const pre = $("codeHighlight");
  const ac = $("autocomplete");
  const acList = $("autocompleteList");
  if (!ta || !pre) return;

  // Initial render
  scheduleHighlight(true);

  // ---------------- Autocomplete ----------------
  let acItems = [];
  let acIndex = 0;

  function hideAutocomplete() {
    if (!ac) return;
    ac.hidden = true;
    acItems = [];
    acIndex = 0;
  }

  function setAutocompleteIndex(nextIdx) {
    if (!acList) return;
    const children = Array.from(acList.children);
    children.forEach((el, i) => el.classList.toggle("active", i === nextIdx));
  }

  function showAutocomplete(items) {
    if (!ac || !acList) return;
    acItems = items;
    acIndex = 0;
    acList.innerHTML = "";

    if (!items.length) {
      hideAutocomplete();
      return;
    }

    for (const item of items) {
      const div = document.createElement("div");
      div.className = "autocomplete-item";
      div.textContent = item;
      div.addEventListener("mousedown", (e) => {
        e.preventDefault(); // keep focus in textarea
        acceptAutocomplete(item);
      });
      acList.appendChild(div);
    }
    setAutocompleteIndex(0);
    ac.hidden = false;
  }

  function acceptAutocomplete(item) {
    const value = ta.value ?? "";
    const pos = ta.selectionStart ?? value.length;
    // get prefix start
    let start = pos;
    while (start > 0 && WORD_CHAR_RE.test(value[start - 1])) start--;
    const prefix = value.slice(start, pos);
    if (!prefix) return;
    const replaced = value.slice(0, start) + item + value.slice(pos);
    ta.value = replaced;
    ta.selectionStart = ta.selectionEnd = start + item.length;
    scheduleHighlight(true);
    hideAutocomplete();
    scheduleSyntaxCheck();
  }

  function collectSymbolsFromCode(code) {
    const out = new Set();
    // Keywords/types/builtins
    TIL_TYPES.forEach((x) => out.add(x));
    TIL_KEYWORDS.forEach((x) => out.add(x));
    TIL_BOOLEANS.forEach((x) => out.add(x));
    TIL_BUILTINS.forEach((x) => out.add(x));
    out.add(TIL_MAIN_FN);

    // User-defined functions
    const fnRe = /\bфункция\s+([_\p{L}\p{M}][_\p{L}\p{M}\p{N}]*)\s*\(/gu;
    let m;
    while ((m = fnRe.exec(code)) !== null) {
      out.add(m[1]);
    }

    // Variable declarations
    const ident = "[_\\p{L}\\p{M}][_\\p{L}\\p{M}\\p{N}]*";
    const primRe = new RegExp(`\\b(бүтүн|чыныгы|сап|белги|логикалык)\\s+(${ident})`, "gu");
    while ((m = primRe.exec(code)) !== null) out.add(m[2]);

    const listRe = new RegExp(`\\bтизме\\s*<[^>]*>\\s+(${ident})`, "gu");
    while ((m = listRe.exec(code)) !== null) out.add(m[1]);

    return Array.from(out);
  }

  function getPrefixInfo(value, pos) {
    let start = pos;
    while (start > 0 && WORD_CHAR_RE.test(value[start - 1])) start--;
    const prefix = value.slice(start, pos);
    return { start, prefix };
  }

  let autocompleteDebounce = null;
  function scheduleAutocompleteUpdate() {
    if (!ac) return;
    if (autocompleteDebounce) clearTimeout(autocompleteDebounce);
    autocompleteDebounce = setTimeout(() => {
      const value = ta.value ?? "";
      const pos = ta.selectionStart ?? value.length;
      const { prefix } = getPrefixInfo(value, pos);
      if (!prefix) {
        hideAutocomplete();
        return;
      }

      const symbols = collectSymbolsFromCode(value);
      const filtered = symbols
        .filter((s) => s.startsWith(prefix))
        .slice(0, 16);

      if (!filtered.length) hideAutocomplete();
      else showAutocomplete(filtered);
    }, 80);
  }

  // Keep overlay in sync with textarea scrolling
  ta.addEventListener("scroll", () => {
    pre.scrollTop = ta.scrollTop;
    pre.scrollLeft = ta.scrollLeft;
  });

  ta.addEventListener("keydown", (e) => {
    if (e.key === "Tab") {
      if (ac && ac.hidden === false && acItems.length) {
        e.preventDefault();
        acceptAutocomplete(acItems[acIndex] ?? acItems[0]);
        return;
      }
      e.preventDefault();
      const insert = " ".repeat(INDENT_UNIT);
      const start = ta.selectionStart ?? 0;
      const end = ta.selectionEnd ?? 0;
      const value = ta.value ?? "";
      ta.value = value.slice(0, start) + insert + value.slice(end);
      ta.selectionStart = ta.selectionEnd = start + insert.length;
      scheduleHighlight();
      return;
    }

    if (ac && ac.hidden === false && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
      e.preventDefault();
      const next = e.key === "ArrowDown" ? Math.min(acIndex + 1, acItems.length - 1) : Math.max(acIndex - 1, 0);
      acIndex = next;
      setAutocompleteIndex(acIndex);
      return;
    }

    if (e.key === "Enter") {
      e.preventDefault();
      const start = ta.selectionStart ?? 0;
      const end = ta.selectionEnd ?? start;
      const value = ta.value ?? "";
      const level = braceLevelUpTo(value, start);
      const indentStr = " ".repeat(level * INDENT_UNIT);
      const insert = "\n" + indentStr;
      ta.value = value.slice(0, start) + insert + value.slice(end);
      ta.selectionStart = ta.selectionEnd = start + insert.length;
      scheduleHighlight();
      lastKeyWasBrace = false;
      return;
    }

    if (e.key === "{" || e.key === "}") {
      lastKeyWasBrace = true;
    } else {
      lastKeyWasBrace = false;
    }
  });

  ta.addEventListener("input", () => {
    scheduleHighlight();
    scheduleAutocompleteUpdate();
    scheduleSyntaxCheck();
    if (!lastKeyWasBrace) return;
    if (isApplyingReindent) return;
    isApplyingReindent = true;
    try {
      reindentCurrentLine();
    } finally {
      isApplyingReindent = false;
    }
    scheduleHighlight(true);
  });
}

async function runCode() {
  const code = $("code").value;
  const input = $("input").value ?? "";

  $("output").textContent = "";
  $("error").textContent = "";

  const resp = await fetch((window.TIL_API_BASE || '') + "/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, input }),
  });

  const noBackend = "Backend жетишсиз. Локально: cd backend && python -m uvicorn backend.app:app --port 8000";
  let data;
  try {
    data = resp.ok ? await resp.json() : null;
    if (!data) throw new Error();
  } catch (_) {
    $("error").textContent = noBackend;
    $("error").className = "error-box";
    return;
  }
  if (data.status === "ok") {
    $("output").textContent = data.output ?? "";
  } else {
    const err = $("error");
    err.textContent = data.error ?? "Unknown error";
    err.className = "error-box";
    err.classList.remove("compile-success");
  }
}

async function checkSyntax() {
  const code = $("code").value;

  $("error").textContent = "";
  $("error").classList.remove("compile-success");

  const resp = await fetch((window.TIL_API_BASE || '') + "/api/compile", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });

  const noBackend = "Backend жетишсиз. Локально: cd backend && python -m uvicorn backend.app:app --port 8000";
  let data;
  try {
    data = resp.ok ? await resp.json() : null;
    if (!data) throw new Error();
  } catch (_) {
    const err = $("error");
    err.textContent = noBackend;
    err.className = "error-box";
    return;
  }
  const err = $("error");
  if (data.ok) {
    err.textContent = window.t ? window.t("syntax_ok") : "Синтаксис корректен.";
    err.className = "error-box compile-success";
  } else {
    const first = Array.isArray(data.diagnostics) && data.diagnostics.length ? data.diagnostics[0] : null;
    const loc =
      first && first.line != null
        ? ` (строка ${first.line}${first.column != null ? `, колонка ${first.column}` : ""})`
        : "";
    err.textContent =
      (first ? first.message : data.error) ??
      (window.t ? window.t("syntax_error_fallback") : "Ошибка проверки");
    err.className = "error-box";
    err.classList.remove("compile-success");
    if (loc && !String(err.textContent).includes("строка")) err.textContent += loc;
  }
}

function showTaskContext(task) {
  const lang = window.getUILang ? window.getUILang() : "ru";
  const isKy = lang === "ky";

  const ctx = $("taskContext");
  $("taskContextTitle").textContent = `${task.id}. ${isKy ? task.title_ky : task.title}`;
  $("taskContextStatement").textContent = isKy ? task.statement_ky : task.statement;
  $("taskContextInput").textContent = task.example_in || "—";
  $("taskContextOutput").textContent = task.example_out || "—";
  ctx.style.display = "block";
  if (task.example_in) {
    const raw = String(task.example_in ?? "");
    // With line-based `окуу()`: numeric inputs should go one token per line.
    // Heuristic: if example is only numbers separated by whitespace, convert to lines.
    const numericOnly = /^-?\d+(\s+-?\d+)*$/u.test(raw.trim());
    $("input").value = numericOnly ? raw.replace(/\s+/g, "\n") : raw;
  }
}

async function loadTaskFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const taskId = params.get("task");
  if (!taskId) return;

  try {
    let resp = await fetch((window.TIL_API_BASE || '') + `/api/tasks/${taskId}`);
    if (!resp.ok) {
      resp = await fetch("tasks.json");
      if (resp.ok) {
        const tasks = await resp.json();
        const task = tasks.find((t) => String(t.id) === String(taskId));
        if (task) showTaskContext(task);
        return;
      }
    }
    if (resp.ok) {
      const task = await resp.json();
      showTaskContext(task);
    }
  } catch (_) {}
}

function init() {
  $("runBtn").addEventListener("click", runCode);
  $("compileBtn").addEventListener("click", checkSyntax);
  $("formatBtn")?.addEventListener("click", formatCode);
  installCodeEditor();
  document.querySelectorAll(".example, .example-card").forEach((el) => {
    el.addEventListener("click", () => setExample(el.dataset.name));
  });

  loadTaskFromUrl().then(() => {
    if (!new URLSearchParams(window.location.search).get("task")) {
      setExample("min");
    }
  });
}

init();

