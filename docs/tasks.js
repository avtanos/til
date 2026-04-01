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
const HINT_LS_PREFIX = "til_task_hint_step_v1:";

const TASK_HINTS = {
  base: [
    {
      ru: "Сначала внимательно выпиши вход и выход. Подумай, какое значение нужно посчитать и вывести.",
      ky: "Адегенде киргизүү/чыгарууну так жаз. Кайсы маанини эсептеп чыгарыш керек экенин ойлон.",
    },
    {
      ru: "Разбей задачу на шаги: прочитать → обработать → вывести. Не усложняй сразу.",
      ky: "Тапшырманы кадамдарга бөл: окуу → иштетүү → чыгаруу. Дароо татаалдаштырба.",
    },
    {
      ru: "Если нужно выбрать вариант, попробуй использовать условие (эгер / болбосо).",
      ky: "Эгер тандоо керек болсо, шартты колдонуп көр (эгер / болбосо).",
    },
  ],
  sem_incdec: [
    {
      ru: "++i и i++ увеличивают переменную на 1. Подумай, где важно «до» или «после» использования значения.",
      ky: "++i жана i++ өзгөрмөнү 1ге көбөйтөт. Маани «алдын» же «кийин» колдонулушу маанилүүбү ойлон.",
    },
    {
      ru: "Если счётчик меняется на 1 каждый раз — ++/-- делает код короче и понятнее.",
      ky: "Эгер эсептегич ар жолу 1ге өзгөрсө — ++/-- кодду кыска жана түшүнүктүү кылат.",
    },
  ],
  sem_assignop: [
    {
      ru: "x += y — это то же самое, что x = x + y. Удобно для накопления суммы/счётчика.",
      ky: "x += y — бул x = x + y деген менен бирдей. Сумма/эсептегич топтоого ыңгайлуу.",
    },
    {
      ru: "Если переменная постепенно изменяется — используй +=, -=, *= и т.д., чтобы показать намерение.",
      ky: "Эгер өзгөрмө акырындык менен өзгөрсө — +=, -=, *= ж.б. колдонуп, ниетиңди так көрсөт.",
    },
  ],
  sem_input: [
    {
      ru: "окуу() читает по строкам. Для чисел берётся первый токен, для сап — вся строка.",
      ky: "окуу() сап боюнча окуйт. Сандар үчүн биринчи токен, сап үчүн бүт сап алынат.",
    },
    {
      ru: "Проверь: сколько раз вызывается окуу() — столько строк ввода нужно ожидать.",
      ky: "Текшер: окуу() канча жолу чакырылса — ошончо сап киргизүү керек.",
    },
  ],
  sem_list: [
    {
      ru: "Список можно пройти циклом по индексам. Не забудь про узундук(a), чтобы не выйти за границы.",
      ky: "Тизмени индекс менен циклде өтсө болот. узундук(a) текшерип, чекеден чыкпа.",
    },
    {
      ru: "Если нужно хранить несколько значений — подумай о тизме<тип> и доступе a[i].",
      ky: "Бир нече маанини сактоо керек болсо — тизме<тип> жана a[i] жөнүндө ойлон.",
    },
  ],
  sem_class: [
    {
      ru: "класс — это шаблон. Поля доступны через точку: obj.field. Сначала создай объект, потом заполняй поля.",
      ky: "класс — бул шаблон. Талаалар чекит аркылуу: obj.field. Адегенде объект түзүп, анан талааларын толтур.",
    },
    {
      ru: "Если нужно сгруппировать данные (x и y вместе) — класс подходит лучше отдельных переменных.",
      ky: "Маалыматты топтоо керек болсо (x жана y бирге) — класс өзүнчө өзгөрмөлөрдөн ыңгайлуу.",
    },
  ],
};

function hintKeyForTask(taskId) {
  return HINT_LS_PREFIX + String(taskId);
}

function nextHintIndex(taskId, group, total) {
  const key = hintKeyForTask(taskId);
  let step = 0;
  try {
    step = parseInt(localStorage.getItem(key) || "0", 10) || 0;
  } catch (_) {}
  const idx = total ? step % total : 0;
  try {
    localStorage.setItem(key, String(step + 1));
  } catch (_) {}
  return idx;
}

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

function ensureHintModal() {
  let backdrop = document.getElementById("hintModalBackdrop");
  if (backdrop) return backdrop;

  backdrop = document.createElement("div");
  backdrop.id = "hintModalBackdrop";
  backdrop.className = "modal-backdrop";
  backdrop.hidden = true;
  backdrop.style.display = "none";
  backdrop.innerHTML = `
    <div class="modal" role="dialog" aria-modal="true" aria-labelledby="hintModalTitle">
      <div class="modal-head">
        <div class="modal-title" id="hintModalTitle"></div>
        <button type="button" class="ghost-btn modal-close-btn" data-modal-close="1" aria-label="Close">✕</button>
      </div>
      <div class="modal-body">
        <pre class="modal-pre modal-pre-wrap" id="hintModalText"></pre>
      </div>
      <div class="modal-actions">
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

  backdrop.addEventListener("click", (e) => {
    if (e.target === backdrop) close();
  });

  backdrop.querySelectorAll("[data-modal-close]").forEach((btn) => {
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

  return backdrop;
}

function typewriteTo(el, text) {
  if (!el) return;
  const full = String(text ?? "");
  if (el._tilTypeTimer) clearInterval(el._tilTypeTimer);
  el.textContent = "";
  let i = 0;
  const speed = 12;
  el._tilTypeTimer = setInterval(() => {
    i++;
    el.textContent = full.slice(0, i);
    if (i >= full.length) {
      clearInterval(el._tilTypeTimer);
      el._tilTypeTimer = null;
    }
  }, speed);
}

function openHintModal(task) {
  const lang = window.getUILang ? window.getUILang() : "ru";
  const isKy = lang === "ky";
  const group = (task.group || "base");

  const explicit = isKy ? task.hint_ky : task.hint;
  const hasExplicit = typeof explicit === "string" && explicit.trim().length > 0;
  const hints = TASK_HINTS[group] || TASK_HINTS.base;
  const idx = nextHintIndex(task.id, group, hints.length);
  const hintObj = hints[idx] || hints[0];
  const hintText = hasExplicit ? explicit : (isKy ? hintObj.ky : hintObj.ru);

  const backdrop = ensureHintModal();
  const titleEl = document.getElementById("hintModalTitle");
  const textEl = document.getElementById("hintModalText");

  if (titleEl) {
    const base = `${task.id}. ${isKy ? task.title_ky : task.title}`;
    const suffix = isKy ? "— Ишара" : "— Подсказка";
    titleEl.textContent = `${base} ${suffix}`;
  }
  if (textEl) {
    typewriteTo(textEl, hintText);
  }

  backdrop.hidden = false;
  backdrop.style.display = "flex";
  document.body.classList.add("modal-open");
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
          <button type="button" class="ghost-btn task-hint-btn" data-hint-task="${escapeHtml(String(t.id))}">
            <span data-lang="ru">Подсказка</span><span data-lang="kg">Ишара</span>
          </button>
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

  list.querySelectorAll("[data-hint-task]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      const id = btn.getAttribute("data-hint-task");
      const task = ALL_TASKS.find((x) => String(x.id) === String(id));
      if (!task) return;
      openHintModal(task);
    });
  });

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
