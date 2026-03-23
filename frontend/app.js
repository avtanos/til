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
    err.textContent = data.error ?? (window.t ? window.t("syntax_error_fallback") : "Ошибка проверки");
    err.className = "error-box";
    err.classList.remove("compile-success");
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
  if (task.example_in) $("input").value = task.example_in;
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

