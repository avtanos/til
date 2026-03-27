const DIFF_STR = {
  1: { ru: "Лёгкая", ky: "Жеңил" },
  2: { ru: "Средняя", ky: "Орто" },
  3: { ru: "Сложная", ky: "Кыйын" },
};

let ALL_TASKS = [];
let ACTIVE_GROUP = "all";

const GROUP_LABELS = {
  all: { ru: "Все", ky: "Баары" },
  base: { ru: "Олимпиадные", ky: "Олимпиада" },
  sem_incdec: { ru: "Семантика: ++/--", ky: "Семантика: ++/--" },
  sem_assignop: { ru: "Семантика: += -= *= /= %=", ky: "Семантика: += -= *= /= %=" },
  sem_input: { ru: "Семантика: окуу()", ky: "Семантика: окуу()" },
  sem_list: { ru: "Семантика: списки []", ky: "Семантика: тизме []" },
  sem_class: { ru: "Семантика: класс и поля", ky: "Семантика: класс жана талаалар" },
};

const SOLUTION_LS_PREFIX = "til_task_solution_v1:";

function lsKeyForTask(taskId) {
  return SOLUTION_LS_PREFIX + String(taskId);
}

function getSavedSolution(taskId) {
  try {
    const raw = localStorage.getItem(lsKeyForTask(taskId));
    if (!raw) return null;
    const obj = JSON.parse(raw);
    if (!obj || typeof obj.code !== "string") return null;
    return obj;
  } catch (_) {
    return null;
  }
}

function ensureSolutionModal() {
  let backdrop = document.getElementById("solutionModalBackdrop");
  if (backdrop) return backdrop;

  backdrop = document.createElement("div");
  backdrop.id = "solutionModalBackdrop";
  backdrop.className = "modal-backdrop";
  backdrop.hidden = true;
  backdrop.style.display = "none";
  backdrop.innerHTML = `
    <div class="modal" role="dialog" aria-modal="true" aria-labelledby="solutionModalTitle">
      <div class="modal-head">
        <div class="modal-title" id="solutionModalTitle"></div>
        <button type="button" class="ghost-btn modal-close-btn" data-modal-close="1" aria-label="Close">✕</button>
      </div>
      <div class="modal-body">
        <pre class="modal-pre" id="solutionModalCode"></pre>
      </div>
      <div class="modal-actions">
        <button type="button" class="chip-btn" id="solutionModalCopyBtn">
          <span data-lang="ru">Копировать</span><span data-lang="kg">Көчүрүү</span>
        </button>
        <button type="button" class="ghost-btn" data-modal-close="1">
          <span data-lang="ru">Закрыть</span><span data-lang="kg">Жабуу</span>
        </button>
      </div>
    </div>
  `;
  document.body.appendChild(backdrop);

  const close = () => {
    backdrop.hidden = true;
    backdrop.style.display = "none";
    document.body.classList.remove("modal-open");
  };

  const modal = backdrop.querySelector(".modal");

  // Click outside closes
  backdrop.addEventListener("click", (e) => {
    if (e.target === backdrop) close();
  });

  // Close buttons: bind directly (click + pointerdown)
  const closeBtns = backdrop.querySelectorAll("[data-modal-close]");
  closeBtns.forEach((btn) => {
    const onClose = (e) => {
      e.preventDefault();
      e.stopPropagation();
      close();
    };
    btn.addEventListener("click", onClose);
    btn.addEventListener("pointerdown", onClose);
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && backdrop.hidden === false) close();
  });

  function copyTextFallback(text) {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "true");
    ta.style.position = "fixed";
    ta.style.top = "-1000px";
    ta.style.left = "-1000px";
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
    } catch (_) {}
    document.body.removeChild(ta);
  }

  const copyBtn = backdrop.querySelector("#solutionModalCopyBtn");
  const doCopy = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    const code = backdrop.querySelector("#solutionModalCode")?.textContent ?? "";
    if (!code) return;

    // UI feedback: "Copied" label (RU/KG)
    try {
      const ruSpan = copyBtn?.querySelector('[data-lang="ru"]');
      const kgSpan = copyBtn?.querySelector('[data-lang="kg"]');
      if (ruSpan && !ruSpan.dataset.orig) ruSpan.dataset.orig = ruSpan.textContent ?? "";
      if (kgSpan && !kgSpan.dataset.orig) kgSpan.dataset.orig = kgSpan.textContent ?? "";
      if (ruSpan) ruSpan.textContent = "Скопирована";
      if (kgSpan) kgSpan.textContent = "Көчүрүлдү";
      clearTimeout(copyBtn?._tilCopyResetTimer);
      copyBtn._tilCopyResetTimer = setTimeout(() => {
        try {
          if (ruSpan && ruSpan.dataset.orig != null) ruSpan.textContent = ruSpan.dataset.orig;
          if (kgSpan && kgSpan.dataset.orig != null) kgSpan.textContent = kgSpan.dataset.orig;
        } catch (_) {}
      }, 1200);
    } catch (_) {}

    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(code);
      } else {
        copyTextFallback(code);
      }
    } catch (_) {
      copyTextFallback(code);
    }
  };
  copyBtn?.addEventListener("click", doCopy);
  copyBtn?.addEventListener("pointerdown", doCopy);

  return backdrop;
}

function openSolutionModal(task, saved) {
  const backdrop = ensureSolutionModal();
  const lang = window.getUILang ? window.getUILang() : "ru";
  const isKy = lang === "ky";

  const title = document.getElementById("solutionModalTitle");
  const codeEl = document.getElementById("solutionModalCode");
  if (title) {
    const base = `${task.id}. ${isKy ? task.title_ky : task.title}`;
    const suffix = isKy ? "— Чечим" : "— Решение";
    title.textContent = `${base} ${suffix}`;
  }
  if (codeEl) {
    if (saved && typeof saved.code === "string" && saved.code.trim()) codeEl.textContent = saved.code;
    else
      codeEl.textContent = isKy
        ? "Бул тапшырма үчүн сизде сакталган туура чечим азырынча жок."
        : "У вас ещё нет сохранённого правильного решения для этой задачи.";
  }

  backdrop.hidden = false;
  backdrop.style.display = "flex";
  document.body.classList.add("modal-open");
}

function renderTasks() {
  const list = document.getElementById("taskList");
  const lang = window.getUILang ? window.getUILang() : "ru";
  const isKy = lang === "ky";

  const filtered =
    ACTIVE_GROUP === "all"
      ? ALL_TASKS
      : ALL_TASKS.filter((t) => (t.group || "base") === ACTIVE_GROUP);

  list.innerHTML = filtered
    .map((t) => {
      const saved = getSavedSolution(t.id);
      const has = !!(saved && typeof saved.code === "string" && saved.code.trim());
      return `
      <div class="task-item" data-task-id="${escapeHtml(String(t.id))}">
        <a href="index.html?task=${t.id}" class="task-open">
          <span class="task-id">${t.id}</span>
          <div class="task-content">
            <div class="task-title">${escapeHtml(isKy ? t.title_ky : t.title)}</div>
            <div class="task-meta">
              ${escapeHtml(isKy ? t.title : t.title_ky)} · ${escapeHtml((DIFF_STR[t.difficulty] && DIFF_STR[t.difficulty][lang]) || "—")}
            </div>
          </div>
        </a>

        <div class="task-actions">
          <button type="button" class="chip-btn task-solution-btn${has ? " task-solution-btn-has" : ""}" data-solution-task="${escapeHtml(String(t.id))}">
            <span data-lang="ru">Решение</span><span data-lang="kg">Чечим</span>
          </button>
          <span class="task-difficulty task-difficulty-${t.difficulty}">
            ${(DIFF_STR[t.difficulty] && DIFF_STR[t.difficulty][lang]) || "—"}
          </span>
        </div>
      </div>
    `;
    })
    .join("");

  list.querySelectorAll("[data-solution-task]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      const id = btn.getAttribute("data-solution-task");
      const task = ALL_TASKS.find((x) => String(x.id) === String(id));
      if (!task) return;
      const saved = getSavedSolution(task.id);
      openSolutionModal(task, saved);
    });
  });
}

function renderGroupTabs() {
  const el = document.getElementById("taskGroupTabs");
  if (!el) return;

  const lang = window.getUILang ? window.getUILang() : "ru";

  const presentGroups = new Set(ALL_TASKS.map((t) => t.group || "base"));

  const order = ["all", "base", "sem_incdec", "sem_assignop", "sem_input", "sem_list", "sem_class"];
  const buttons = order
    .filter((g) => g === "all" || presentGroups.has(g))
    .map((g) => {
      const label = (GROUP_LABELS[g] && GROUP_LABELS[g][lang]) || String(g);
      const active = ACTIVE_GROUP === g ? " active" : "";
      return `<button type="button" class="chip-btn task-group-btn${active}" data-group="${escapeHtml(g)}">${escapeHtml(label)}</button>`;
    })
    .join("");

  el.innerHTML = buttons;

  el.querySelectorAll("[data-group]").forEach((btn) => {
    btn.addEventListener("click", () => {
      ACTIVE_GROUP = btn.dataset.group || "all";
      renderGroupTabs();
      renderTasks();
    });
  });
}

async function loadTasks() {
  const list = document.getElementById("taskList");
  const lang = window.getUILang ? window.getUILang() : "ru";
  const isKy = lang === "ky";

  try {
    let resp = await fetch((window.TIL_API_BASE || '') + "/api/tasks");
    if (!resp.ok) resp = await fetch("tasks.json");
    const tasks = await resp.json();
    ALL_TASKS = tasks;
    ACTIVE_GROUP = "all";
    renderGroupTabs();
    renderTasks();
  } catch (e) {
    list.innerHTML = `<p style="color: var(--muted);">${window.t ? window.t("tasks_error") : "Ошибка загрузки задач."}</p>`;
  }
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

loadTasks();
