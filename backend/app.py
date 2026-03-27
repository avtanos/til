from __future__ import annotations

import os

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

