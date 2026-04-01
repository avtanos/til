const $ = (id) => document.getElementById(id);

function getLang() {
  const l = (window.getUILang ? window.getUILang() : "ru") || "ru";
  return l === "ky" ? "ky" : "ru";
}

function typewriteTo(el, text) {
  if (!el) return;
  const full = String(text ?? "");
  if (el._tilTypeTimer) clearInterval(el._tilTypeTimer);
  el.textContent = "";
  let i = 0;
  const speed = 10;
  el._tilTypeTimer = setInterval(() => {
    i++;
    el.textContent = full.slice(0, i);
    if (i >= full.length) {
      clearInterval(el._tilTypeTimer);
      el._tilTypeTimer = null;
    }
  }, speed);
}

function collectTopicContext(topicKey) {
  // Simple mapping to sections by heading order; fallback: full page text (shortened).
  const map = {
    types: 1,
    if: 2,
    for: 2,
    while: 2,
    do: 2,
    logic: 3,
    io: 5,
    list: 6,
    class: 7,
    ops: 10,
    comments: 11,
  };

  const idx = map[topicKey] || 2;
  const sections = Array.from(document.querySelectorAll(".semantics-section"));
  const sec = sections.find((s) => {
    const h = s.querySelector("h2");
    return h && h.textContent && h.textContent.trim().startsWith(String(idx) + ".");
  });

  const text = (sec ? sec.innerText : document.body.innerText) || "";
  return text.slice(0, 4500);
}

async function postJsonWithApiFallback(path, payload) {
  const localBase = "http://127.0.0.1:8000";
  // Prefer explicit API base; fallback to local backend on localhost.
  const host = window.location && window.location.hostname ? window.location.hostname : "";
  const isLocalHost = host === "localhost" || host === "127.0.0.1" || host === "0.0.0.0";
  const primaryBase = window.TIL_API_BASE || (isLocalHost ? localBase : "");
  const bases = [];
  if (primaryBase) bases.push(primaryBase);
  // NOTE: avoid same-origin POSTs when frontend is served by a static server (e.g. http.server),
  // because it returns 501 for POST and confuses debugging.
  if (!bases.includes(localBase) && isLocalHost) bases.push(localBase);

  let lastErr = null;
  for (const base of bases) {
    const url = base + path;
    const ctrl = new AbortController();
    // Ollama can be slow, especially for study-plan generation.
    const mode = payload && typeof payload.mode === "string" ? payload.mode : "";
    const timeoutMs = mode === "plan" ? 180000 : 60000;
    const t = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
      const resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: ctrl.signal,
      });
      if (!resp.ok) continue;
      return await resp.json();
    } catch (e) {
      lastErr = e;
    } finally {
      clearTimeout(t);
    }
  }
  throw lastErr || new Error("api request failed");
}

async function runAi(mode) {
  const out = $("semAiOut");
  const status = $("semAiStatus");
  const kidBtn = $("semExplainKidBtn");
  const moreBtn = $("semMoreExamplesBtn");
  const askBtn = $("semAskBtn");
  const copyBtn = $("semCopyOutBtn");
  const dlBtn = $("semDownloadOutBtn");
  const topic = $("semTopic")?.value || "if";
  const question = $("semQuestion")?.value || "";
  const lang = getLang();
  const ctx = collectTopicContext(topic);

  if (status) status.textContent = lang === "ky" ? "Жооп даярдалып жатат..." : "Готовлю ответ...";
  if (out) out.textContent = "";
  if (copyBtn) copyBtn.style.display = "none";
  if (dlBtn) dlBtn.style.display = "none";
  [kidBtn, moreBtn, askBtn].forEach((b) => b && (b.disabled = true));

  try {
    const data = await postJsonWithApiFallback("/api/ai", {
      mode,
      topic,
      text: ctx,
      question,
      lang,
    });
    if (!data || !data.ok) {
      const err = (data && data.error) || (lang === "ky" ? "Ката: жооп алынган жок." : "Ошибка: ответ не получен.");
      if (status) status.textContent = err;
      if (out) out.textContent = "";
      return;
    }
    if (status) status.textContent = "";
    typewriteTo(out, data.text || "");
    // Show copy/download only for plan output (not for Q&A/explanations)
    if (mode === "plan") {
      if (copyBtn) copyBtn.style.display = "";
      if (dlBtn) dlBtn.style.display = "";
    }
  } catch (e) {
    const msg = String(e && e.message ? e.message : e || "");
    const isAbort = msg.toLowerCase().includes("aborted");
    if (status) {
      status.textContent =
        (lang === "ky"
          ? (isAbort
              ? "Ката: жоопко убакыт жетпей калды (таймаут). Ollama жай иштеп жатат — бир аз күтө тур."
              : "Ката: backend/Ollama жетишсиз. Backend: http://127.0.0.1:8000, Ollama: http://127.0.0.1:11434")
          : "Ошибка: backend/Ollama недоступны. Backend: http://127.0.0.1:8000, Ollama: http://127.0.0.1:11434") +
        (msg ? ` (${msg})` : "");
    }
    if (out) out.textContent = "";
  } finally {
    [kidBtn, moreBtn, askBtn].forEach((b) => b && (b.disabled = false));
  }
}

function collectWizard() {
  const who = document.querySelector('input[name="who"]:checked')?.value || "beginner";
  const goal = document.querySelector('input[name="goal"]:checked')?.value || "basics";
  const duration = $("planDuration")?.value || "1m";
  const durationCustom = $("planDurationCustom")?.value || "";
  const daysWeek = parseInt($("planDaysWeek")?.value || "5", 10) || 5;
  const timesDay = parseInt($("planTimesDay")?.value || "1", 10) || 1;
  const minsSession = parseInt($("planMinsSession")?.value || "30", 10) || 30;
  const uiLang = $("planUiLang")?.value || getLang();
  const age = $("planAge")?.value || "adult";
  const prefs = {
    theory: !!$("prefTheory")?.checked,
    practice: !!$("prefPractice")?.checked,
    short: !!$("prefShort")?.checked,
    detailed: !!$("prefDetailed")?.checked,
  };

  return {
    level:
      who === "olymp" ? "olymp" : who === "has_exp" ? "base" : "beginner",
    who,
    goal,
    duration,
    durationCustom,
    daysWeek,
    timesDay,
    minsSession,
    uiLang,
    age,
    prefs,
  };
}

function wizardSummaryText(meta) {
  const lang = getLang();
  const dur = meta.duration === "custom" ? (meta.durationCustom || "—") : meta.duration;
  const load = `${meta.daysWeek}d/week · ${meta.timesDay}x/day · ${meta.minsSession}min`;
  if (lang === "ky") {
    return `Профиль:\n- who: ${meta.who}\n- goal: ${meta.goal}\n- мөөнөт: ${dur}\n- жүк: ${load}\n- курак: ${meta.age}\n- UI: ${meta.uiLang}\n- ыңгай: theory=${meta.prefs.theory}, practice=${meta.prefs.practice}, short=${meta.prefs.short}, detailed=${meta.prefs.detailed}`;
  }
  return `Профиль:\n- who: ${meta.who}\n- goal: ${meta.goal}\n- срок: ${dur}\n- нагрузка: ${load}\n- возраст: ${meta.age}\n- UI: ${meta.uiLang}\n- удобство: theory=${meta.prefs.theory}, practice=${meta.prefs.practice}, short=${meta.prefs.short}, detailed=${meta.prefs.detailed}`;
}

function initWizard() {
  const backdrop = $("planWizardBackdrop");
  if (!backdrop) return;

  const close = () => {
    backdrop.hidden = true;
    backdrop.style.display = "none";
    document.body.classList.remove("modal-open");
  };

  $("planWizardCloseBtn")?.addEventListener("click", close);
  backdrop.addEventListener("click", (e) => {
    if (e.target === backdrop) close();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && backdrop.hidden === false) close();
  });

  const steps = [1, 2, 3, 4, 5].map((n) => $(`planStep${n}`));
  let step = 1;
  const setStep = (n) => {
    step = Math.max(1, Math.min(5, n));
    steps.forEach((el, idx) => {
      if (!el) return;
      el.style.display = idx + 1 === step ? "" : "none";
    });
    const lbl = $("planWizardStepLabel");
    if (lbl) lbl.textContent = `Step ${step}/5`;
    const nextBtn = $("planNextBtn");
    const genBtn = $("planGenerateBtn");
    if (nextBtn) nextBtn.style.display = step === 5 ? "none" : "";
    if (genBtn) genBtn.style.display = step === 5 ? "" : "none";
    $("planBackBtn") && ($("planBackBtn").disabled = step === 1);

    if (step === 5) {
      const meta = collectWizard();
      const sum = $("planWizardSummary");
      if (sum) sum.textContent = wizardSummaryText(meta);
    }
  };

  $("planBackBtn")?.addEventListener("click", () => setStep(step - 1));
  $("planNextBtn")?.addEventListener("click", () => setStep(step + 1));

  $("planDuration")?.addEventListener("change", () => {
    const v = $("planDuration")?.value || "";
    const custom = $("planDurationCustom");
    if (!custom) return;
    custom.style.display = v === "custom" ? "" : "none";
  });

  $("planGenerateBtn")?.addEventListener("click", async () => {
    const meta = collectWizard();
    close();
    const out = $("semAiOut");
    const status = $("semAiStatus");
    const copyBtn = $("semCopyOutBtn");
    const dlBtn = $("semDownloadOutBtn");
    if (status) status.textContent = getLang() === "ky" ? "План түзүлүүдө..." : "Генерирую план...";
    if (out) out.textContent = "";
    if (copyBtn) copyBtn.style.display = "none";
    if (dlBtn) dlBtn.style.display = "none";
    try {
      const data = await postJsonWithApiFallback("/api/ai", {
        mode: "plan",
        topic: "learning_plan",
        text: "",
        question: "",
        // Generate strictly in active UI language
        lang: getLang(),
        meta,
      });
      if (!data || !data.ok) {
        if (status) status.textContent = (data && data.error) || "Plan error";
        return;
      }
      if (status) status.textContent = "";
      typewriteTo(out, data.text || "");
      if (copyBtn) copyBtn.style.display = "";
      if (dlBtn) dlBtn.style.display = "";
    } catch (e) {
      const msg = String(e && e.message ? e.message : e || "");
      if (status) status.textContent = msg || "api request failed";
    }
  });

  $("semPlanBtn")?.addEventListener("click", () => {
    backdrop.hidden = false;
    backdrop.style.display = "flex";
    document.body.classList.add("modal-open");
    setStep(1);
  });
}

function init() {
  $("semExplainKidBtn")?.addEventListener("click", () => runAi("kid"));
  $("semMoreExamplesBtn")?.addEventListener("click", () => runAi("more_examples"));
  $("semAskBtn")?.addEventListener("click", () => runAi("qa"));
  $("semQuestion")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") runAi("qa");
  });
  initWizard();

  // Copy generated plan/output
  $("semCopyOutBtn")?.addEventListener("click", async (e) => {
    e.preventDefault();
    const btn = $("semCopyOutBtn");
    const out = $("semAiOut")?.textContent ?? "";
    if (!out.trim()) return;

    const lang = getLang();
    const ruSpan = btn?.querySelector?.('[data-lang="ru"]');
    const kgSpan = btn?.querySelector?.('[data-lang="kg"]');
    if (ruSpan && !ruSpan.dataset.orig) ruSpan.dataset.orig = ruSpan.textContent ?? "";
    if (kgSpan && !kgSpan.dataset.orig) kgSpan.dataset.orig = kgSpan.textContent ?? "";

    const setCopied = () => {
      if (ruSpan) ruSpan.textContent = "Скопировано";
      if (kgSpan) kgSpan.textContent = "Көчүрүлдү";
      clearTimeout(btn?._tilCopyResetTimer);
      btn._tilCopyResetTimer = setTimeout(() => {
        try {
          if (ruSpan && ruSpan.dataset.orig != null) ruSpan.textContent = ruSpan.dataset.orig;
          if (kgSpan && kgSpan.dataset.orig != null) kgSpan.textContent = kgSpan.dataset.orig;
        } catch (_) {}
      }, 1200);
    };

    const copyFallback = (text) => {
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
    };

    try {
      if (navigator.clipboard && window.isSecureContext) await navigator.clipboard.writeText(out);
      else copyFallback(out);
      setCopied();
    } catch (_) {
      copyFallback(out);
      setCopied();
    }
  });

  // Download generated plan/output as .txt
  $("semDownloadOutBtn")?.addEventListener("click", (e) => {
    e.preventDefault();
    const out = $("semAiOut")?.textContent ?? "";
    if (!out.trim()) return;
    const blob = new Blob([out], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const ts = new Date();
    const y = ts.getFullYear();
    const m = String(ts.getMonth() + 1).padStart(2, "0");
    const d = String(ts.getDate()).padStart(2, "0");
    a.href = url;
    a.download = `til-plan-${y}-${m}-${d}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 2500);
  });
}

init();

