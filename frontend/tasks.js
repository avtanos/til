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

function renderTasks() {
  const list = document.getElementById("taskList");
  const lang = window.getUILang ? window.getUILang() : "ru";
  const isKy = lang === "ky";

  const filtered =
    ACTIVE_GROUP === "all"
      ? ALL_TASKS
      : ALL_TASKS.filter((t) => (t.group || "base") === ACTIVE_GROUP);

  list.innerHTML = filtered
    .map(
      (t) => `
      <a href="index.html?task=${t.id}" class="task-item">
        <span class="task-id">${t.id}</span>
        <div class="task-content">
          <div class="task-title">${escapeHtml(isKy ? t.title_ky : t.title)}</div>
          <div class="task-meta">
            ${escapeHtml(isKy ? t.title : t.title_ky)} · ${escapeHtml((DIFF_STR[t.difficulty] && DIFF_STR[t.difficulty][lang]) || "—")}
          </div>
        </div>
        <span class="task-difficulty task-difficulty-${t.difficulty}">
          ${(DIFF_STR[t.difficulty] && DIFF_STR[t.difficulty][lang]) || "—"}
        </span>
      </a>
    `
    )
    .join("");
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
