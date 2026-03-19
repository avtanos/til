const I18N = {
  ru: {
    nav_editor: "Редактор",
    nav_tasks: "Задачи",
    nav_semantics: "Семантика языка",
    editor_title: "TIL MVP",
    editor_subtitle: "Язык с кыргызскими ключевыми словами + интерпретатор на сервере",
    card_code: "Код",
    card_input: "Ввод",
    card_output: "Вывод",
    card_errors: "Ошибки / Проверка синтаксиса",
    compile_btn: "Проверить синтаксис",
    run_btn: "Запустить",
    format_hint: "Формат: `башкы()` или функции `функция ...`",
    examples_title: "Примеры",
    examples_hint:
      "В MVP для `окуу()` чтение идет по токенам, разделенным пробелами/переводами строк.",
    syntax_ok: "Синтаксис корректен. Программа готова к выполнению.",
    syntax_error_fallback: "Ошибка проверки",
    ex_min: "Минимум: чыгар",
    ex_cmp: "эгер/болбосо: салыштыруу",
    ex_sum: "үчүн: 1..n суммасы",
    ex_fact: "функция: факториал",
    ex_while: "качан: отсчет",
    ex_dowhile: "жаса..качан: эсептегич",
    ex_logic: "жана/же/эмес",
    ex_arrsum: "тизме: сумма",
    ex_strlen: "узундук: сап узундугу",
    ex_cont: "улантуу/токтот",
    tasks_title: "Задачи",
    tasks_subtitle: "20 олимпиадных задач для языка TIL",
    tasks_loading: "Загрузка...",
    task_input_label: "Ввод:",
    task_output_label: "Вывод:",
    semantics_title: "Семантика языка TIL",
    semantics_subtitle: "Детальное описание синтаксиса на кыргызском и русском языках",
  },
  ky: {
    nav_editor: "Редактор",
    nav_tasks: "Тапшырмалар",
    nav_semantics: "Тил семантикасы",
    editor_title: "TIL MVP",
    editor_subtitle: "Кыргызча ачкыч сөздөр менен тил + сервердеги интерпретатор",
    card_code: "Код",
    card_input: "Киргизүү",
    card_output: "Чыгаруу",
    card_errors: "Каталар / Синтаксисти текшерүү",
    compile_btn: "Синтаксисти текшерүү",
    run_btn: "Иштетүү",
    format_hint: "Формат: `башкы()` же `функция ...`",
    examples_title: "Мисалдар",
    examples_hint:
      "MVPде `окуу()` окуу токендер аркылуу жүрөт: боштук жана сап өтүүлөр менен бөлүнөт.",
    syntax_ok: "Синтаксис туура. Программа аткарууга даяр.",
    syntax_error_fallback: "Текшерүү катасы",
    ex_min: "Минимум: чыгар",
    ex_cmp: "эгер/болбосо: салыштыруу",
    ex_sum: "үчүн: 1..n суммасы",
    ex_fact: "функция: факториал",
    ex_while: "качан: санак",
    ex_dowhile: "жаса..качан: эсептегич",
    ex_logic: "жана/же/эмес",
    ex_arrsum: "тизме: сумма",
    ex_strlen: "узундук: сап узундугу",
    ex_cont: "улантуу/токтот",
    tasks_title: "Тапшырмалар",
    tasks_subtitle: "TIL тили үчүн 20 олимпиадалык тапшырма",
    tasks_loading: "Жүктөлүүдө...",
    task_input_label: "Киргизүү:",
    task_output_label: "Чыгаруу:",
    semantics_title: "TIL тилинин семантикасы",
    semantics_subtitle: "Кыргызча жана орусча боюнча синтаксистин кеңири сүрөттөлүшү",
  },
};

function detectDefaultLang() {
  try {
    const stored = localStorage.getItem("til_ui_lang");
    if (stored === "ru" || stored === "ky") return stored;
  } catch (_) {}

  const nav = (navigator.language || "").toLowerCase();
  if (nav.startsWith("ky")) return "ky";
  return "ru";
}

function getLang() {
  return window.TIL_LANG || detectDefaultLang();
}

function t(key) {
  const lang = getLang();
  return (I18N[lang] && I18N[lang][key]) || I18N.ru[key] || key;
}

function applyI18n() {
  const lang = getLang();
  window.TIL_LANG = lang;

  // For proper fonts/behaviour in some browsers.
  document.documentElement.lang = lang === "ky" ? "ky" : "ru";

  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    el.textContent = t(key);
  });
}

function initLangSelect() {
  const select = document.getElementById("langSelect");
  if (!select) return;

  const lang = detectDefaultLang();
  select.value = lang;

  select.addEventListener("change", () => {
    const newLang = select.value;
    window.TIL_LANG = newLang;
    try {
      localStorage.setItem("til_ui_lang", newLang);
    } catch (_) {}
    applyI18n();
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initLangSelect();
  applyI18n();
});

// Expose helpers for other scripts (app.js / tasks.js).
window.TIL_I18N = I18N;
window.t = t;
window.getUILang = getLang;

