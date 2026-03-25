(function () {
  const KEY = "til_ui_lang";
  const body = document.body;
  let langBtn = null;

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
    if (langBtn) langBtn.classList.toggle("active", lang === "kg");
    if (langBtn) langBtn.textContent = lang === "kg" ? "KG" : "RU";
    document.documentElement.lang = lang === "ru" ? "ru" : "ky";

    // Keep "Project" navigation consistent with active UI language.
    const projectLink = document.getElementById("projectNavLink");
    if (projectLink) {
      projectLink.href = lang === "ru" ? "project-ru.html" : "project-kg.html";
    }

    // If user opened the "wrong" project page for the active UI language, switch to the matching one.
    // (Avoids confusion when only one menu item is visible.)
    try {
      const file = String(window.location && window.location.pathname ? window.location.pathname : "")
        .split("/")
        .pop()
        .toLowerCase();
      const want = lang === "ru" ? "project-ru.html" : "project-kg.html";
      const isProject = file === "project-ru.html" || file === "project-kg.html";
      if (isProject && file !== want) {
        window.location.replace(want);
      }
    } catch (_) {}
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

  function initLangToggle() {
    langBtn = document.getElementById("langToggleBtn");
    setLang(getStored());
    if (!langBtn) return;
    langBtn.addEventListener("click", function () {
      const next = getStored() === "kg" ? "ru" : "kg";
      setLang(next);
    });
  }

  // Works even if scripts are loaded late.
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initLangToggle);
  } else {
    initLangToggle();
  }
})();
