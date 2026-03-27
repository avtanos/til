from __future__ import annotations

import time
from dataclasses import dataclass

from .ast import (
    ArrayLiteral,
    Assign,
    AssignOp,
    BinOp,
    BreakStmt,
    CallExpr,
    CastExpr,
    ClassDef,
    ContinueStmt,
    DoWhileStmt,
    DotExpr,
    DotRef,
    Expr,
    ExprStmt,
    FunctionDef,
    IncDecExpr,
    IfStmt,
    IndexExpr,
    IndexRef,
    InputExpr,
    Literal,
    Program,
    ReturnStmt,
    Stmt,
    UnaryOp,
    VarDecl,
    VarRef,
    WhileStmt,
    ForStmt,
)
from .errors import TILRuntimeError
from .typesys import Type, TypeKind


BUILTIN_PRINT = "чыгар"
BUILTIN_INPUT = "окуу"
BUILTIN_LENGTH = "узундук"


class _ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


class _BreakSignal(Exception):
    pass


class _ContinueSignal(Exception):
    pass


@dataclass
class CompiledCtx:
    classes: dict[str, ClassDef]
    functions: dict[str, FunctionDef]
    function_return_types: dict[str, Type]
    main_stmts: list[Stmt]
    input_expected_types: dict[tuple[int, int], Type] | None = None


class Interpreter:
    def __init__(
        self,
        ctx: CompiledCtx,
        input_text: str,
        max_steps: int = 200000,
        time_limit_s: float = 2.0,
        max_call_depth: int = 50,
    ):
        self.ctx = ctx
        self.steps = 0
        self.max_steps = max_steps
        self.time_limit_s = time_limit_s
        self.max_call_depth = max_call_depth
        self.start_time = time.monotonic()

        # Line-based input:
        # - allows sentences with spaces to be read as a single `окуу()` value
        # - each `окуу()` consumes the next input line
        self.input_lines = input_text.splitlines()
        self.input_i = 0

        # runtime output
        self.output_lines: list[str] = []

        self.call_depth = 0
        self.env_stack: list[dict[str, tuple[Type, object]]] = [{}]

    def _check_limits(self) -> None:
        if self.steps >= self.max_steps:
            raise TILRuntimeError("Ката: иштөө кадамдарынын саны чектен ашты.")
        if (self.steps % 2000) == 0:
            if (time.monotonic() - self.start_time) > self.time_limit_s:
                raise TILRuntimeError("Ката: убакыт ашты.")

    def run(self) -> str:
        if "башкы" in self.ctx.functions:
            self.call_function("башкы", [])
        else:
            self.exec_block(self.ctx.main_stmts)
        return "\n".join(self.output_lines)

    # -------------------- Values & casting --------------------

    def _default_value(self, t: Type) -> object:
        if t.kind == TypeKind.INT:
            return 0
        if t.kind == TypeKind.FLOAT:
            return 0.0
        if t.kind == TypeKind.STRING:
            return ""
        if t.kind == TypeKind.CHAR:
            return ""
        if t.kind == TypeKind.BOOL:
            return False
        if t.kind == TypeKind.LIST:
            return []
        if t.kind == TypeKind.CLASS and t.class_name and self.ctx.classes:
            cls = self.ctx.classes.get(t.class_name)
            if cls:
                return {fn: self._default_value(ft) for ft, fn in cls.fields}
        return None

    def _format_value(self, v: object) -> str:
        if isinstance(v, bool):
            return "чын" if v else "жалган"
        if isinstance(v, float):
            # avoid noisy 1.0 output
            if abs(v - round(v)) < 1e-9:
                return str(int(round(v)))
            return str(v)
        if isinstance(v, list):
            return " ".join(self._format_value(x) for x in v)
        return str(v)

    def _cast_value(self, v: object, dst: Type, loc: object | None = None) -> object:
        if dst.kind == TypeKind.UNKNOWN:
            return v

        # numeric
        if dst.kind == TypeKind.INT:
            if isinstance(v, bool):
                raise TILRuntimeError("Ката: логиканы бүтүнгө айландырууга болбойт.")
            if isinstance(v, int):
                return v
            if isinstance(v, float):
                if abs(v - round(v)) > 1e-9:
                    raise TILRuntimeError("Ката: бөлчөк санды бүтүнгө айландырууга болбойт.")
                return int(round(v))
            if isinstance(v, str):
                try:
                    return int(v.strip())
                except ValueError:
                    raise TILRuntimeError("Ката: бул маанини бүтүн түрүнө айлантуу мүмкүн эмес.")
            raise TILRuntimeError("Ката: түрдүн дал келбеши.")

        if dst.kind == TypeKind.FLOAT:
            if isinstance(v, bool):
                raise TILRuntimeError("Ката: логиканы чыныгыга айландырууга болбойт.")
            if isinstance(v, (int, float)):
                return float(v)
            if isinstance(v, str):
                try:
                    return float(v.strip())
                except ValueError:
                    raise TILRuntimeError("Ката: бул маанини чыныгы түрүнө айлантуу мүмкүн эмес.")
            raise TILRuntimeError("Ката: түрдүн дал келбеши.")

        if dst.kind == TypeKind.STRING:
            if isinstance(v, list):
                return " ".join(self._format_value(x) for x in v)
            if isinstance(v, str):
                return v
            # allow primitives -> string
            if isinstance(v, (int, float, bool)):
                return self._format_value(v)
            raise TILRuntimeError("Ката: түрдүн дал келбеши.")

        if dst.kind == TypeKind.CHAR:
            if isinstance(v, str):
                if len(v) != 1:
                    raise TILRuntimeError("Ката: белгинин узундугу 1 болуусу керек.")
                return v
            raise TILRuntimeError("Ката: белгиге айландыруу мүмкүн эмес.")

        if dst.kind == TypeKind.BOOL:
            if isinstance(v, bool):
                return v
            if isinstance(v, str):
                s = v.strip().lower()
                if s in {"чын", "true", "1"}:
                    return True
                if s in {"жалган", "false", "0"}:
                    return False
                raise TILRuntimeError("Ката: логикалык маанини таанууга мүмкүн эмес.")
            if isinstance(v, int):
                return v != 0
            raise TILRuntimeError("Ката: логикалык түргө айландыруу мүмкүн эмес.")

        if dst.kind == TypeKind.LIST:
            if not isinstance(v, list):
                raise TILRuntimeError("Ката: тизмеге айландыруу мүмкүн эмес.")
            item = dst.item
            if item is None:
                return v
            return [self._cast_value(x, item, loc=loc) for x in v]

        return v

    # -------------------- Variables --------------------

    def _env_get(self, name: str) -> tuple[Type, object]:
        for scope in reversed(self.env_stack):
            if name in scope:
                return scope[name]
        raise TILRuntimeError(f"Ката: переменная '{name}' аныкталган эмес.")

    def _env_set(self, name: str, value: object, t: Type) -> None:
        for scope in reversed(self.env_stack):
            if name in scope:
                scope[name] = (t, value)
                return
        self.env_stack[-1][name] = (t, value)

    # -------------------- Execution --------------------

    def exec_block(self, stmts: list[Stmt]) -> None:
        self.env_stack.append({})
        try:
            for s in stmts:
                self.steps += 1
                self._check_limits()
                self.exec_stmt(s)
        finally:
            self.env_stack.pop()

    def exec_stmt(self, s: Stmt) -> None:
        if isinstance(s, VarDecl):
            init_v = self._default_value(s.var_type) if s.init is None else self._eval_expr(s.init)
            init_v = self._cast_value(init_v, s.var_type, loc=s.loc)
            self.env_stack[-1][s.name] = (s.var_type, init_v)
            return

        if isinstance(s, Assign):
            self._exec_assign(s, classes=self.ctx.classes or {})
            return

        if isinstance(s, AssignOp):
            self._exec_assign_op(s)
            return

        if isinstance(s, IfStmt):
            cond = self._eval_expr(s.cond)
            if not isinstance(cond, bool):
                raise TILRuntimeError("Ката: 'эгер' шарт логикалык болуш керек.")
            if cond:
                self.exec_block(s.then_body)
            elif s.else_body is not None:
                self.exec_block(s.else_body)
            return

        if isinstance(s, WhileStmt):
            while True:
                self.steps += 1
                self._check_limits()
                cond = self._eval_expr(s.cond)
                if not isinstance(cond, bool):
                    raise TILRuntimeError("Ката: 'качан' шарт логикалык болуш керек.")
                if not cond:
                    break
                try:
                    self.exec_block(s.body)
                except _BreakSignal:
                    break
                except _ContinueSignal:
                    continue
            return

        if isinstance(s, ForStmt):
            self.exec_stmt(s.init)
            while True:
                self.steps += 1
                self._check_limits()
                cond = self._eval_expr(s.cond)
                if not isinstance(cond, bool):
                    raise TILRuntimeError("Ката: 'үчүн' шарт логикалык болуш керек.")
                if not cond:
                    break
                try:
                    self.exec_block(s.body)
                except _BreakSignal:
                    break
                except _ContinueSignal:
                    pass
                # step executed even after continue (like C)
                if isinstance(s.step, Assign):
                    self._exec_assign(s.step)
                else:
                    self._exec_assign_op(s.step)
            return

        if isinstance(s, DoWhileStmt):
            while True:
                self.steps += 1
                self._check_limits()
                try:
                    self.exec_block(s.body)
                except _ContinueSignal:
                    pass
                except _BreakSignal:
                    break
                cond = self._eval_expr(s.cond)
                if not isinstance(cond, bool):
                    raise TILRuntimeError("Ката: 'качан' шарт логикалык болуш керек.")
                if not cond:
                    break
            return

        if isinstance(s, BreakStmt):
            raise _BreakSignal()

        if isinstance(s, ContinueStmt):
            raise _ContinueSignal()

        if isinstance(s, ReturnStmt):
            val = None if s.value is None else self._eval_expr(s.value)
            raise _ReturnSignal(val)

        if isinstance(s, ExprStmt):
            _ = self._eval_expr(s.expr)
            return

        raise TILRuntimeError("Ката: непредвиденный оператор.")

    def _exec_assign(self, a: Assign, classes: dict[str, ClassDef] | None = None) -> None:
        classes = classes or {}
        if isinstance(a.target, DotRef):
            obj_v = self._eval_expr(a.target.obj)
            if not isinstance(obj_v, dict):
                raise TILRuntimeError("Ката: талаа текст объект үчүн гана.")
            if a.target.field not in obj_v:
                raise TILRuntimeError(f"Ката: '{a.target.field}' талаасы жок.")
            v = self._eval_expr(a.value)
            # get field type from class for casting
            if isinstance(a.target.obj, VarRef) and classes:
                t, _ = self._env_get(a.target.obj.name)
                if t.kind == TypeKind.CLASS and t.class_name in classes:
                    cls = classes[t.class_name]
                    field_t = next((ft for ft, fn in cls.fields if fn == a.target.field), None)
                    if field_t:
                        v = self._cast_value(v, field_t, loc=a.loc)
            obj_v[a.target.field] = v
            return

        if isinstance(a.target, VarRef):
            t, _old = self._env_get(a.target.name)
            v = self._eval_expr(a.value)
            v = self._cast_value(v, t, loc=a.loc)
            self._env_set(a.target.name, v, t)
            return

        if isinstance(a.target, IndexRef):
            arr_t, arr_v = self._env_get(a.target.array.name)
            if arr_t.kind != TypeKind.LIST or arr_t.item is None:
                raise TILRuntimeError("Ката: индекс коюуга тек массив колдонулат.")
            idx_v = self._eval_expr(a.target.index)
            idx_v = self._cast_value(idx_v, Type.from_name("бүтүн"), loc=a.loc)
            if not isinstance(idx_v, int):
                raise TILRuntimeError("Ката: массив индекси бүтүн болуш керек.")
            if idx_v < 0 or idx_v >= len(arr_v):  # type: ignore[arg-type]
                raise TILRuntimeError("Ката: индекс тизменин чегинен чыгып кетти.")
            item_t = arr_t.item
            v = self._eval_expr(a.value)
            v = self._cast_value(v, item_t, loc=a.loc)
            arr_v[idx_v] = v  # type: ignore[index]
            return

        raise TILRuntimeError("Ката: присваивание үчүн левосторонняя часть туура эмес.")

    def _exec_assign_op(self, a: AssignOp) -> None:
        """x += y → x = x + y; string += concat; numeric += -=% *=% /=% %= """
        if isinstance(a.target, VarRef):
            t, old = self._env_get(a.target.name)
            v = self._eval_expr(a.value)
            if a.op == "+=":
                if t.kind == TypeKind.STRING:
                    v = self._cast_value(v, t, loc=a.loc)
                    new = (old if isinstance(old, str) else str(old)) + (v if isinstance(v, str) else str(v))
                else:
                    v = self._cast_value(v, t, loc=a.loc)
                    if not isinstance(old, (int, float)) or isinstance(old, bool):
                        raise TILRuntimeError("Ката: '+=' сан үчүн гана.")
                    if not isinstance(v, (int, float)) or isinstance(v, bool):
                        raise TILRuntimeError("Ката: '+=' сан үчүн гана.")
                    new = old + v
            elif a.op == "-=":
                v = self._cast_value(v, t, loc=a.loc)
                new = self._cast_value((old if isinstance(old, (int, float)) else 0) - (v if isinstance(v, (int, float)) else 0), t, loc=a.loc)
            elif a.op == "*=":
                v = self._cast_value(v, t, loc=a.loc)
                new = self._cast_value((old if isinstance(old, (int, float)) else 0) * (v if isinstance(v, (int, float)) else 0), t, loc=a.loc)
            elif a.op == "/=":
                v = self._cast_value(v, t, loc=a.loc)
                rv = v if isinstance(v, (int, float)) else 0
                if rv == 0:
                    raise TILRuntimeError("Ката: нөлгө бөлүү мүмкүн эмес.")
                new = (old if isinstance(old, (int, float)) else 0) / rv
                new = self._cast_value(new, t, loc=a.loc)
            elif a.op == "%=":
                v = self._cast_value(v, t, loc=a.loc)
                lo = old if isinstance(old, int) and not isinstance(old, bool) else 0
                ro = v if isinstance(v, int) and not isinstance(v, bool) else 0
                if ro == 0:
                    raise TILRuntimeError("Ката: нөлгө бөлүү мүмкүн эмес.")
                new = lo % ro
            else:
                raise TILRuntimeError("Ката: белгисиз AssignOp.")
            self._env_set(a.target.name, new, t)
            return

        if isinstance(a.target, IndexRef):
            arr_t, arr_v = self._env_get(a.target.array.name)
            idx_v = self._cast_value(self._eval_expr(a.target.index), Type.from_name("бүтүн"), loc=a.loc)
            if not isinstance(idx_v, int) or idx_v < 0 or idx_v >= len(arr_v):
                raise TILRuntimeError("Ката: индекс тизменин чегинен чыгып кетти.")
            item_t = arr_t.item or Type.unknown()
            old = arr_v[idx_v]
            v = self._eval_expr(a.value)
            v = self._cast_value(v, item_t, loc=a.loc)
            if a.op == "+=":
                if item_t.kind == TypeKind.STRING:
                    new = (old if isinstance(old, str) else str(old)) + (v if isinstance(v, str) else str(v))
                else:
                    new = (old if isinstance(old, (int, float)) else 0) + (v if isinstance(v, (int, float)) else 0)
            elif a.op == "-=":
                new = (old if isinstance(old, (int, float)) else 0) - (v if isinstance(v, (int, float)) else 0)
            elif a.op == "*=":
                new = (old if isinstance(old, (int, float)) else 0) * (v if isinstance(v, (int, float)) else 0)
            elif a.op == "/=":
                rv = v if isinstance(v, (int, float)) else 0
                if rv == 0:
                    raise TILRuntimeError("Ката: нөлгө бөлүү мүмкүн эмес.")
                new = (old if isinstance(old, (int, float)) else 0) / rv
            elif a.op == "%=":
                ro = v if isinstance(v, int) and not isinstance(v, bool) else 0
                if ro == 0:
                    raise TILRuntimeError("Ката: нөлгө бөлүү мүмкүн эмес.")
                new = (old if isinstance(old, int) and not isinstance(old, bool) else 0) % ro
            else:
                raise TILRuntimeError("Ката: белгисиз AssignOp.")
            arr_v[idx_v] = self._cast_value(new, item_t, loc=a.loc)
            return

        raise TILRuntimeError("Ката: AssignOp үчүн туура эмес цель.")

    # -------------------- Expressions --------------------

    def _read_input(self, expected_type: Type | None, loc: object) -> object:
        """Read one line; parse by expected type: scalar→first token, string→full line, list→whitespace-split."""
        if self.input_i >= len(self.input_lines):
            raise TILRuntimeError("Ката: киргизүү жетишсиз.")
        line = self.input_lines[self.input_i]
        self.input_i += 1

        if expected_type is None or expected_type.kind == TypeKind.UNKNOWN:
            return line

        if expected_type.kind == TypeKind.STRING:
            return line

        if expected_type.kind == TypeKind.LIST:
            tokens = line.split()
            item_t = expected_type.item
            if item_t is None:
                return tokens
            return [self._cast_value(t, item_t, loc=loc) for t in tokens]

        # scalar: int, float, bool, char — first token only
        tokens = line.split()
        if not tokens:
            return self._default_value(expected_type)
        first = tokens[0]
        return self._cast_value(first, expected_type, loc=loc)

    def _eval_expr(self, e: Expr):
        if isinstance(e, Literal):
            return e.value

        if isinstance(e, InputExpr):
            expected = None
            if self.ctx.input_expected_types:
                expected = self.ctx.input_expected_types.get((e.loc.line, e.loc.column))
            return self._read_input(expected, e.loc)

        if isinstance(e, VarRef):
            _t, v = self._env_get(e.name)
            return v

        if isinstance(e, DotExpr):
            obj_v = self._eval_expr(e.obj)
            if not isinstance(obj_v, dict):
                raise TILRuntimeError("Ката: талаа текст объект үчүн гана.")
            if e.field not in obj_v:
                raise TILRuntimeError(f"Ката: '{e.field}' талаасы жок.")
            return obj_v[e.field]

        if isinstance(e, CastExpr):
            v = self._eval_expr(e.expr)
            return self._cast_value(v, e.target_type, loc=e.loc)

        if isinstance(e, ArrayLiteral):
            return [self._eval_expr(it) for it in e.items]

        if isinstance(e, IndexExpr):
            arr_v = self._eval_expr(e.array)
            idx_v = self._cast_value(self._eval_expr(e.index), Type.from_name("бүтүн"), loc=e.loc)
            if not isinstance(idx_v, int):
                raise TILRuntimeError("Ката: массив индекси бүтүн болуш керек.")
            if idx_v < 0 or idx_v >= len(arr_v):  # type: ignore[arg-type]
                raise TILRuntimeError("Ката: индекс тизменин чегинен чыгып кетти.")
            return arr_v[idx_v]  # type: ignore[index]

        if isinstance(e, IncDecExpr):
            if isinstance(e.target, VarRef):
                t, old = self._env_get(e.target.name)
                if not isinstance(old, (int, float)) or isinstance(old, bool):
                    raise TILRuntimeError("Ката: ++/-- сан үчүн гана.")
                delta = 1 if e.op == "++" else -1
                new = self._cast_value(
                    (old + delta) if isinstance(old, float) else (int(old) + delta),
                    t,
                    loc=e.loc,
                )
                self._env_set(e.target.name, new, t)
                return old if e.is_postfix else new

            arr_t, arr_v = self._env_get(e.target.array.name)
            idx_v = self._cast_value(self._eval_expr(e.target.index), Type.from_name("бүтүн"), loc=e.loc)
            if not isinstance(idx_v, int) or idx_v < 0 or idx_v >= len(arr_v):
                raise TILRuntimeError("Ката: индекс тизменин чегинен чыгып кетти.")
            old = arr_v[idx_v]
            if not isinstance(old, (int, float)) or isinstance(old, bool):
                raise TILRuntimeError("Ката: ++/-- сан үчүн гана.")
            item_t = arr_t.item or Type.from_name("бүтүн")
            delta = 1 if e.op == "++" else -1
            new = self._cast_value(
                (old + delta) if isinstance(old, float) else (int(old) + delta),
                item_t,
                loc=e.loc,
            )
            arr_v[idx_v] = new
            return old if e.is_postfix else new

        if isinstance(e, UnaryOp):
            r = self._eval_expr(e.right)
            if e.op == "-":
                if isinstance(r, (int, float)) and not isinstance(r, bool):
                    return -r
                raise TILRuntimeError("Ката: унар '-' сан үчүн гана иштейт.")
            if e.op == "!":
                if isinstance(r, bool):
                    return not r
                raise TILRuntimeError("Ката: 'эмес' логикалык үчүн гана иштейт.")
            raise TILRuntimeError("Ката: белгисиз унар операция.")

        if isinstance(e, BinOp):
            if e.op == "&&":
                left = self._eval_expr(e.left)
                if not isinstance(left, bool):
                    raise TILRuntimeError("Ката: логикалык 'жана' үчүн логикалык аргумент керек.")
                if not left:
                    return False
                right = self._eval_expr(e.right)
                if not isinstance(right, bool):
                    raise TILRuntimeError("Ката: логикалык 'жана' үчүн логикалык аргумент керек.")
                return left and right

            if e.op == "||":
                left = self._eval_expr(e.left)
                if not isinstance(left, bool):
                    raise TILRuntimeError("Ката: логикалык 'же' үчүн логикалык аргумент керек.")
                if left:
                    return True
                right = self._eval_expr(e.right)
                if not isinstance(right, bool):
                    raise TILRuntimeError("Ката: логикалык 'же' үчүн логикалык аргумент керек.")
                return left or right

            left = self._eval_expr(e.left)
            right = self._eval_expr(e.right)

            # String concatenation: if either operand is a string, `+` concatenates.
            if e.op == "+" and (isinstance(left, str) or isinstance(right, str)):
                return (left if isinstance(left, str) else self._format_value(left)) + (
                    right if isinstance(right, str) else self._format_value(right)
                )

            if e.op in {"+", "-", "*", "/"}:
                if not isinstance(left, (int, float)) or not isinstance(right, (int, float)) or isinstance(left, bool) or isinstance(right, bool):
                    raise TILRuntimeError("Ката: арифметикалык операция сан үчүн гана иштейт.")
                if e.op == "+":
                    return left + right
                if e.op == "-":
                    return left - right
                if e.op == "*":
                    return left * right
                if e.op == "/":
                    if right == 0:
                        raise TILRuntimeError("Ката: нөлгө бөлүү мүмкүн эмес.")
                    # int/int => trunc toward zero
                    if isinstance(left, int) and isinstance(right, int) and not isinstance(left, bool) and not isinstance(right, bool):
                        return int(left / right)
                    return left / right

            if e.op == "%":
                if not isinstance(left, int) or not isinstance(right, int) or isinstance(left, bool) or isinstance(right, bool):
                    raise TILRuntimeError("Ката: '%' тек бүтүн сандар үчүн.")
                if right == 0:
                    raise TILRuntimeError("Ката: нөлгө бөлүү мүмкүн эмес.")
                return left % right

            if e.op in {"==", "!=", ">", ">=", "<", "<="}:
                if e.op == "==":
                    return left == right
                if e.op == "!=":
                    return left != right
                if e.op == ">":
                    return left > right
                if e.op == ">=":
                    return left >= right
                if e.op == "<":
                    return left < right
                if e.op == "<=":
                    return left <= right

            raise TILRuntimeError("Ката: белгисиз бинар операция.")

        if isinstance(e, CallExpr):
            return self._call_expr(e)

        raise TILRuntimeError("Ката: белгисиз туюнтма.")

    def _call_expr(self, c: CallExpr):
        if c.name == BUILTIN_INPUT:
            # fallback: treat окуу() as string token
            if len(c.args) != 0:
                raise TILRuntimeError("Ката: окуу() аргумент албайт.")
            return self._read_input_token()

        if c.name == BUILTIN_PRINT:
            if len(c.args) != 1:
                raise TILRuntimeError("Ката: чыгар() бир аргумент алат.")
            v = self._eval_expr(c.args[0])
            self.output_lines.append(self._format_value(v))
            return None

        if c.name == BUILTIN_LENGTH:
            if len(c.args) != 1:
                raise TILRuntimeError("Ката: узундук() бир аргумент алат.")
            v = self._eval_expr(c.args[0])
            if isinstance(v, (str, list)):
                return len(v)
            raise TILRuntimeError("Ката: узундук() тек сап же тизме үчүн.")

        fn = self.ctx.functions.get(c.name)
        if fn is None:
            raise TILRuntimeError(f"Ката: функция '{c.name}' табылган жок.")
        if len(c.args) != len(fn.params):
            raise TILRuntimeError("Ката: функция аргументтеринин саны дал келбейт.")

        args_vals = [self._eval_expr(a) for a in c.args]
        return self.call_function(c.name, args_vals)

    def call_function(self, name: str, args_vals: list[object]):
        fn = self.ctx.functions.get(name)
        if fn is None:
            raise TILRuntimeError(f"Ката: функция '{name}' табылган жок.")
        if len(args_vals) != len(fn.params):
            raise TILRuntimeError("Ката: туура эмес аргумент саны.")

        self.call_depth += 1
        if self.call_depth > self.max_call_depth:
            raise TILRuntimeError("Ката: максималдык рекурсия тереңдиги ашты.")

        self.env_stack.append({})
        try:
            # bind params with casting
            for (p_type, p_name), raw in zip(fn.params, args_vals):
                val = self._cast_value(raw, p_type, loc=fn.loc)
                self.env_stack[-1][p_name] = (p_type, val)

            try:
                for s in fn.body:
                    self.steps += 1
                    self._check_limits()
                    self.exec_stmt(s)
            except _ReturnSignal as r:
                # if function return is expected, cast it to return type if known
                rv = r.value
                rt = self.ctx.function_return_types.get(name, Type.unknown())
                if rt.kind != TypeKind.VOID and rt.kind != TypeKind.UNKNOWN:
                    rv = self._cast_value(rv, rt, loc=fn.loc)
                return rv
        finally:
            self.env_stack.pop()
            self.call_depth -= 1

        # no explicit return
        return None

