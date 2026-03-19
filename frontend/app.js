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

async function runCode() {
  const code = $("code").value;
  const input = $("input").value ?? "";

  $("output").textContent = "";
  $("error").textContent = "";

  const resp = await fetch("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, input }),
  });

  const data = await resp.json();
  if (data.status === "ok") {
    $("output").textContent = data.output ?? "";
  } else {
    $("error").textContent = data.error ?? "Unknown error";
  }
}

async function checkSyntax() {
  const code = $("code").value;

  $("error").textContent = "";
  $("error").classList.remove("compile-success");

  const resp = await fetch("/api/compile", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });

  const data = await resp.json();
  if (data.ok) {
    $("error").textContent = window.t ? window.t("syntax_ok") : "Синтаксис корректен.";
    $("error").classList.add("compile-success");
  } else {
    $("error").textContent =
      data.error ?? (window.t ? window.t("syntax_error_fallback") : "Ошибка проверки");
    $("error").classList.remove("compile-success");
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
    const resp = await fetch(`/api/tasks/${taskId}`);
    if (resp.ok) {
      const task = await resp.json();
      showTaskContext(task);
    }
  } catch (_) {}
}

function init() {
  $("runBtn").addEventListener("click", runCode);
  $("compileBtn").addEventListener("click", checkSyntax);
  document.querySelectorAll(".example").forEach((btn) => {
    btn.addEventListener("click", () => setExample(btn.dataset.name));
  });

  loadTaskFromUrl().then(() => {
    if (!new URLSearchParams(window.location.search).get("task")) {
      setExample("min");
    }
  });
}

init();

