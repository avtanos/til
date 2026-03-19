(function () {
  const KEY = "til_ui_lang";
  const body = document.body;
  let ruBtn = null;
  let kgBtn = null;

  function getStored() {
    try {
      const v = localStorage.getItem(KEY);
      return v === "ru" ? "ru" : "kg";
    } catch (_) {
      return "kg";
    }
  }

  function setLang(lang) {
    body.classList.remove("lang-ru", "lang-kg");
    body.classList.add("lang-" + lang);
    try {
      localStorage.setItem(KEY, lang);
    } catch (_) {}
    if (ruBtn) ruBtn.classList.toggle("active", lang === "ru");
    if (kgBtn) kgBtn.classList.toggle("active", lang === "kg");
    document.documentElement.lang = lang === "ru" ? "ru" : "ky";
  }

  (function initNow() {
    setLang(getStored());
  })();

  window.getUILang = function () {
    return body.classList.contains("lang-kg") ? "ky" : "ru";
  };

  window.t = function (key) {
    const lang = window.getUILang();
    const map = {
      syntax_ok: { ru: "Синтаксис корректен. Программа готова к выполнению.", ky: "Синтаксис туура. Программа аткарууга даяр." },
      syntax_error_fallback: { ru: "Ошибка проверки", ky: "Текшерүү катасы" },
      tasks_loading: { ru: "Загрузка...", ky: "Жүктөлүүдө..." },
      tasks_error: { ru: "Ошибка загрузки задач.", ky: "Тапшырмаларды жүктөөдө ката." },
    };
    const m = map[key];
    return (m && m[lang]) || (m && m.ru) || key;
  };

  document.addEventListener("DOMContentLoaded", function () {
    ruBtn = document.getElementById("ruBtn");
    kgBtn = document.getElementById("kgBtn");
    setLang(getStored());
    if (ruBtn) ruBtn.addEventListener("click", function () { setLang("ru"); });
    if (kgBtn) kgBtn.addEventListener("click", function () { setLang("kg"); });
  });
})();
