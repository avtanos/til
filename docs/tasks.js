const DIFF_STR = {
  1: { ru: "Лёгкая", ky: "Жеңил" },
  2: { ru: "Средняя", ky: "Орто" },
  3: { ru: "Сложная", ky: "Кыйын" },
};

async function loadTasks() {
  const list = document.getElementById("taskList");
  const lang = window.getUILang ? window.getUILang() : "ru";
  const isKy = lang === "ky";

  try {
    let resp = await fetch((window.TIL_API_BASE || '') + "/api/tasks");
    if (!resp.ok) resp = await fetch("tasks.json");
    const tasks = await resp.json();
    list.innerHTML = tasks
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
