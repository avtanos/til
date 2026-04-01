from __future__ import annotations

import os

import json
import urllib.error
import urllib.request

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .tasks_data import TASKS
from .tillang import Interpreter, CompiledCtx, compile_program, parse
from .tillang.errors import TILCompileError, TILRuntimeError
from .storage import init_db, last_runs, save_run
from .tillang.semantic import CompiledProgram


app = FastAPI(title="TIL Platform KYRGYZ")

frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    code: str
    input: str | None = ""


class RunResponse(BaseModel):
    status: str
    output: str = ""
    error: str | None = None


class CompileRequest(BaseModel):
    code: str


class Diagnostic(BaseModel):
    message: str
    line: int | None = None
    column: int | None = None


class CompileResponse(BaseModel):
    ok: bool
    error: str | None = None
    diagnostics: list[Diagnostic] = []


class AiRequest(BaseModel):
    mode: str
    topic: str | None = ""
    text: str | None = ""
    question: str | None = ""
    lang: str | None = "ru"
    model: str | None = None
    meta: dict | None = None


class AiResponse(BaseModel):
    ok: bool
    text: str = ""
    error: str | None = None


def _ollama_generate(*, prompt: str, model: str | None = None) -> str:
    base = os.environ.get("OLLAMA_BASE", "http://127.0.0.1:11434")
    # Default to a small model commonly available on Windows installs.
    use_model = model or os.environ.get("OLLAMA_MODEL", "llama3.2:1b")
    url = base.rstrip("/") + "/api/generate"
    payload = {"model": use_model, "prompt": prompt, "stream": False}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        # Ollama can be slow (especially for long plans); allow a longer timeout.
        with urllib.request.urlopen(req, timeout=300) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            obj = json.loads(raw)
            return str(obj.get("response") or "")
    except urllib.error.HTTPError as e:
        # Ollama can return model-not-found or other JSON error payloads.
        try:
            body = e.read().decode("utf-8", errors="replace")
            obj = json.loads(body)
            msg = obj.get("error") or body
        except Exception:  # noqa: BLE001
            msg = ""
        extra = f" ({msg})" if msg else ""
        raise RuntimeError(f"Ollama вернул ошибку{extra}. Проверь модель: {use_model}") from e
    except TimeoutError as e:
        raise RuntimeError("Ollama отвечает слишком долго. Подожди или используй более лёгкую модель (например llama3.2:1b).") from e
    except urllib.error.URLError as e:
        raise RuntimeError("Ollama недоступен. Запусти: ollama serve") from e
    except Exception as e:  # noqa: BLE001
        raise RuntimeError("Ошибка запроса к Ollama") from e


def _build_ai_prompt(req: AiRequest) -> str:
    lang = (req.lang or "ru").lower()
    topic = (req.topic or "").strip()
    text = (req.text or "").strip()
    question = (req.question or "").strip()

    if req.mode == "kid":
        if lang == "ky":
            return (
                "Сен программалоону жаңы үйрөнгөн балага түшүндүргөн мугалимсиң.\n"
                "Тапшырма: теорияны өтө жөнөкөй кылып түшүндүр, 2-3 аналогия бер, бирок даяр чечим бербе.\n"
                f"Тема: {topic}\n"
                f"Материал:\n{text}\n"
            )
        return (
            "Ты наставник и объясняешь программирование как ребёнку.\n"
            "Задача: упростить теорию, дать 2-3 аналогии, без готового решения.\n"
            f"Тема: {topic}\n"
            f"Материал:\n{text}\n"
        )

    if req.mode == "more_examples":
        if lang == "ky":
            return (
                "TIL тили үчүн мисалдарды чыгар.\n"
                "Талап: 6 кыска мисал, ар биринде окуу() жана чыгар() болсо жакшы. Ар мисалдан кийин 1 сап түшүндүр.\n"
                f"Тема: {topic}\n"
                f"Теория/контекст:\n{text}\n"
            )
        return (
            "Сгенерируй примеры кода на языке TIL.\n"
            "Требование: 6 коротких примеров, желательно с окуу() и чыгар(). После каждого примера 1 строка пояснения.\n"
            f"Тема: {topic}\n"
            f"Теория/контекст:\n{text}\n"
        )

    if req.mode == "plan":
        # Study plan generator: expects meta questionnaire
        meta = req.meta or {}
        if lang == "ky":
            return (
                "Сен TIL боюнча окуу планы түзгөн AI-насаатчысың.\n"
                "Сенин милдетиң: кооз текст жазуу эмес, структуралуу план куруу.\n"
                "Формула: План = деңгээл + максат + мөөнөт + жүк + темп + диагностикалык боштуктар.\n"
                "Эрежелер:\n"
                "- Даяр код/чечим бербе.\n"
                "- Эгер колдонуучу новичок болсо, дароо функция/массив/олимпиадага өтпө.\n"
                "- Ар модулда: кыска теория + практика (канча тапшырма) + бүтүү критерийи.\n"
                "- Модулдар көз карандылыгы сакталсын.\n\n"
                "Модулдардын матрицасы (TIL):\n"
                "1) Киришүү (кыйынчылык 1, 20–40 мин, көз карандылык жок)\n"
                "2) Ввод/вывод окуу()/чыгар() (1, 40–60 мин, deps:1)\n"
                "3) Өзгөрмөлөр жана типтер (1, 60–90 мин, deps:2)\n"
                "4) Арифметика (1, 60–90 мин, deps:3)\n"
                "5) Шарт эгер/болбосо (1, 60–90 мин, deps:4)\n"
                "6) Цикл качан/үчүн/жаса..качан (2, 90–140 мин, deps:5)\n"
                "7) Саптар (2, 60–120 мин, deps:3)\n"
                "8) Тизмелер (3, 90–160 мин, deps:6)\n"
                "9) Функциялар (3, 90–160 мин, deps:6)\n"
                "10) Логика жана аралаш тапшырмалар (3, 120–200 мин, deps:5,6)\n"
                "11) Олимпиадалык шаблондор (4, 200–400 мин, deps:10)\n"
                "12) Итог/мини-проект (2–4, 120–240 мин, deps:10)\n\n"
                f"Анкета (JSON):\n{json.dumps(meta, ensure_ascii=False)}\n\n"
                "Чыгыш форматы:\n"
                "## Профиль\n"
                "- ...\n"
                "## Жүктөм эсептөөсү\n"
                "- жалпы минут/жума, жалпы жума/күн\n"
                "## План (жума боюнча)\n"
                "- Жума 1: модулдар..., тапшырмалар..., критерий...\n"
                "...\n"
                "## Диагностика\n"
                "- кайсы жерлер алсыз болсо эмне кылуу керек\n"
            )
        return (
            "Ты AI-наставник, который строит учебный план по TIL.\n"
            "Твоя задача: не просто красивый текст, а структурный план.\n"
            "Формула: План = уровень + цель + срок + нагрузка + темп + диагностические пробелы.\n"
            "Правила:\n"
            "- Не давай готовые решения и длинные листинги.\n"
            "- Если пользователь новичок — не начинай с массивов/функций/олимпиад.\n"
            "- В каждом модуле: мини-теория, практика (кол-во задач), критерий завершения.\n"
            "- Соблюдай зависимости модулей.\n\n"
            "Матрица модулей (TIL):\n"
            "1) Введение в TIL (сложн 1, 20–40 мин, deps: —)\n"
            "2) Ввод/вывод окуу()/чыгар() (1, 40–60 мин, deps:1)\n"
            "3) Переменные и типы (1, 60–90 мин, deps:2)\n"
            "4) Арифметика (1, 60–90 мин, deps:3)\n"
            "5) Условие эгер/болбосо (1, 60–90 мин, deps:4)\n"
            "6) Циклы качан/үчүн/жаса..качан (2, 90–140 мин, deps:5)\n"
            "7) Строки (2, 60–120 мин, deps:3)\n"
            "8) Списки/массивы (3, 90–160 мин, deps:6)\n"
            "9) Функции (3, 90–160 мин, deps:6)\n"
            "10) Логика и комбинированные задачи (3, 120–200 мин, deps:5,6)\n"
            "11) Олимпиадные шаблоны (4, 200–400 мин, deps:10)\n"
            "12) Итоговый блок / мини‑проект (2–4, 120–240 мин, deps:10)\n\n"
            f"Анкета (JSON):\n{json.dumps(meta, ensure_ascii=False)}\n\n"
            "Формат ответа:\n"
            "## Профиль\n"
            "- ...\n"
            "## Расчёт нагрузки\n"
            "- минут/день, минут/неделю, общий объём\n"
            "## План по неделям\n"
            "- Неделя 1: модули..., задачи..., критерий...\n"
            "...\n"
            "## Диагностика пробелов\n"
            "- что проверить и как подтянуть\n"
        )

    # mode == qa
    if lang == "ky":
        return (
            "Сен TIL синтаксиси боюнча жооп берүүчү жардамчысың.\n"
            "Эрежелер: кыска, түшүнүктүү; айырмасын мисал менен көрсөт; даяр толук чечим жазба.\n"
            f"Суроо: {question}\n"
            f"Контекст:\n{text}\n"
        )
    return (
        "Ты помощник по синтаксису языка TIL.\n"
        "Правила: коротко и ясно; покажи разницу на мини-примере; не пиши полное решение задачи.\n"
        f"Вопрос: {question}\n"
        f"Контекст:\n{text}\n"
    )


@app.post("/api/ai", response_model=AiResponse)
def api_ai(req: AiRequest):
    if req.mode not in {"kid", "more_examples", "qa", "plan"}:
        return AiResponse(ok=False, text="", error="Invalid mode")
    prompt = _build_ai_prompt(req)
    try:
        out = _ollama_generate(prompt=prompt, model=req.model)
        return AiResponse(ok=True, text=out.strip(), error=None)
    except RuntimeError as e:
        return AiResponse(ok=False, text="", error=str(e))


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/api/last-runs")
def api_last_runs(limit: int = 20):
    return last_runs(limit=limit)


@app.get("/api/tasks")
def api_tasks():
    return TASKS


@app.get("/api/tasks/{task_id}")
def api_task(task_id: int):
    for t in TASKS:
        if t["id"] == task_id:
            return t
    return JSONResponse(status_code=404, content={"detail": "Task not found"})


@app.post("/api/compile", response_model=CompileResponse)
def api_compile(req: CompileRequest):
    """Проверка синтаксиса и семантики без выполнения."""
    code = (req.code or "").strip()
    if not code:
        return CompileResponse(ok=False, error="Ката: код пуст.", diagnostics=[])
    try:
        ast = parse(code)
        compile_program(ast)
        return CompileResponse(ok=True, error=None, diagnostics=[])
    except TILCompileError as e:
        diag = Diagnostic(message=e.message, line=e.line, column=e.column)
        return CompileResponse(ok=False, error=str(e), diagnostics=[diag])


@app.post("/api/run", response_model=RunResponse)
def api_run(req: RunRequest):
    code = (req.code or "").strip()
    if not code:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "output": "", "error": "Ката: код пуст."},
        )

    try:
        ast = parse(code)
        compiled: CompiledProgram = compile_program(ast)
        ctx = CompiledCtx(classes=compiled.classes, functions=compiled.functions, function_return_types=compiled.function_return_types, main_stmts=compiled.main_stmts, input_expected_types=compiled.input_expected_types)
        interpreter = Interpreter(ctx=ctx, input_text=req.input or "")
        output = interpreter.run()
        save_run(code=code, input_text=req.input, output_text=output, error_text=None, status="ok")
        return RunResponse(status="ok", output=output, error=None)
    except TILCompileError as e:
        err = str(e)
        save_run(code=code, input_text=req.input, output_text="", error_text=err, status="compile_error")
        return RunResponse(status="error", output="", error=err)
    except TILRuntimeError as e:
        err = str(e)
        save_run(code=code, input_text=req.input, output_text="", error_text=err, status="runtime_error")
        return RunResponse(status="error", output="", error=err)
    except Exception as e:  # noqa: BLE001
        # Avoid leaking internals. MVP: return generic error.
        err = f"Ката: непредвиденная ошибка. {e.__class__.__name__}"
        save_run(code=code, input_text=req.input, output_text="", error_text=err, status="internal_error")
        return RunResponse(status="error", output="", error=err)


# Static files mount should come after API routes, so `/api/...` is not intercepted.
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")

