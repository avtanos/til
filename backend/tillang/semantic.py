from __future__ import annotations

from dataclasses import dataclass, field

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
    NodeLoc,
    Program,
    ReturnStmt,
    Stmt,
    UnaryOp,
    VarDecl,
    VarRef,
    WhileStmt,
    ForStmt,
)
from .errors import TILCompileError
from .typesys import Type, TypeKind, is_numeric, promote_numeric, types_equal


@dataclass(frozen=True)
class CompiledProgram:
    classes: dict[str, ClassDef]
    functions: dict[str, FunctionDef]
    main_stmts: list[Stmt]
    function_return_types: dict[str, Type]
    input_expected_types: dict[tuple[int, int], "Type"] = field(default_factory=dict)


BUILTIN_PRINT = "чыгар"
BUILTIN_INPUT = "окуу"
BUILTIN_LENGTH = "узундук"


def compile_program(program: Program, max_passes: int = 5) -> CompiledProgram:
    classes = {c.name: c for c in program.classes}
    functions = {f.name: f for f in program.functions}

    # Init return types as UNKNOWN; we'll try to converge by re-analyzing returns.
    ret_types: dict[str, Type] = {name: Type.unknown() for name in functions.keys()}
    input_types: dict[tuple[int, int], Type] = {}

    for _pass in range(max_passes):
        changed = False
        for fn in functions.values():
            env: list[dict[str, Type]] = [{}]
            for p_type, p_name in fn.params:
                env[-1][p_name] = p_type

            observed_return_type = _analyze_statements(
                fn.body,
                env=env,
                functions=functions,
                ret_types=ret_types,
                expected_return_type=None,
                input_types=input_types,
                classes=classes,
            )
            if observed_return_type is None:
                # no return found; keep UNKNOWN to not block MVP
                continue

            old = ret_types.get(fn.name, Type.unknown())
            new = observed_return_type
            merged = _merge_return_types(old, new)
            if not types_equal(old, merged):
                ret_types[fn.name] = merged
                changed = True

        if not changed:
            break

    # Final analysis with casts insertion.
    _analyze_statements(
        program.main_stmts,
        env=[{}],
        functions=functions,
        ret_types=ret_types,
        expected_return_type=None,
        allow_top_level=True,
        input_types=input_types,
        classes=classes,
    )
    # Also validate each function more strictly and insert casts by rebuilding AST.
    # For simplicity of MVP, we only type-check here without storing transformed AST.
    return CompiledProgram(classes=classes, functions=functions, main_stmts=program.main_stmts, function_return_types=ret_types, input_expected_types=dict(input_types))


def _merge_return_types(a: Type, b: Type) -> Type:
    if a.kind == TypeKind.UNKNOWN:
        return b
    if b.kind == TypeKind.UNKNOWN:
        return a
    if a.kind == b.kind:
        return a
    if is_numeric(a) and is_numeric(b):
        return promote_numeric(a, b)
    # Incompatible returns; keep UNKNOWN to defer error until assignment.
    return Type.unknown()


def _lookup(env: list[dict[str, Type]], name: str) -> Type | None:
    for scope in reversed(env):
        if name in scope:
            return scope[name]
    return None


def _declare(env: list[dict[str, Type]], name: str, t: Type, loc: NodeLoc) -> None:
    if name in env[-1]:
        raise TILCompileError(f"Ката: переменная '{name}' уже объявлена.", loc.line, loc.column)
    env[-1][name] = t


def _analyze_statements(
    stmts: list[Stmt],
    env: list[dict[str, Type]],
    functions: dict[str, FunctionDef],
    ret_types: dict[str, Type],
    expected_return_type: Type | None,
    allow_top_level: bool = False,
    input_types: dict[tuple[int, int], Type] | None = None,
    classes: dict[str, ClassDef] | None = None,
) -> Type | None:
    observed_return_type: Type | None = None

    for s in stmts:
        if isinstance(s, VarDecl):
            if s.var_type.kind == TypeKind.CLASS and classes and s.var_type.class_name and s.var_type.class_name not in classes:
                raise TILCompileError(f"Ката: '{s.var_type.class_name}' классты табуу мүмкүн эмес.", s.loc.line, s.loc.column)
            init_expr = s.init
            if init_expr is None:
                _declare(env, s.name, s.var_type, s.loc)
                continue

            _declare(env, s.name, s.var_type, s.loc)
            expr_t = _infer_expr_type(init_expr, env, functions, ret_types, expected=s.var_type, input_types=input_types, classes=classes)
            # type mismatch handled in infer
            _ = expr_t

        elif isinstance(s, Assign):
            _check_assign(s, env, functions, ret_types, input_types, classes)

        elif isinstance(s, AssignOp):
            _check_assign_op(s, env, functions, ret_types, input_types, classes)

        elif isinstance(s, IfStmt):
            cond_t = _infer_expr_type(s.cond, env, functions, ret_types, expected=Type.from_name("логикалык"), input_types=input_types, classes=classes)
            if cond_t.kind != TypeKind.BOOL and cond_t.kind != TypeKind.UNKNOWN:
                raise TILCompileError("Ката: условие 'эгер' должно быть логическим.", s.loc.line, s.loc.column)
            env.append({})
            _analyze_statements(s.then_body, env, functions, ret_types, expected_return_type, input_types=input_types, classes=classes)
            env.pop()
            if s.else_body is not None:
                env.append({})
                _analyze_statements(s.else_body, env, functions, ret_types, expected_return_type, input_types=input_types, classes=classes)
                env.pop()

        elif isinstance(s, WhileStmt):
            cond_t = _infer_expr_type(s.cond, env, functions, ret_types, expected=Type.from_name("логикалык"), input_types=input_types, classes=classes)
            if cond_t.kind != TypeKind.BOOL and cond_t.kind != TypeKind.UNKNOWN:
                raise TILCompileError("Ката: условие 'качан' должно быть логическим.", s.loc.line, s.loc.column)
            env.append({})
            _analyze_statements(s.body, env, functions, ret_types, expected_return_type, input_types=input_types, classes=classes)
            env.pop()

        elif isinstance(s, ForStmt):
            env.append({})
            _analyze_for(s, env, functions, ret_types, input_types, classes)
            env.pop()

        elif isinstance(s, DoWhileStmt):
            env.append({})
            _analyze_statements(s.body, env, functions, ret_types, expected_return_type, input_types=input_types, classes=classes)
            cond_t = _infer_expr_type(s.cond, env, functions, ret_types, expected=Type.from_name("логикалык"), input_types=input_types, classes=classes)
            if cond_t.kind != TypeKind.BOOL and cond_t.kind != TypeKind.UNKNOWN:
                raise TILCompileError("Ката: условие 'качан' должно быть логическим.", s.loc.line, s.loc.column)
            env.pop()

        elif isinstance(s, BreakStmt) or isinstance(s, ContinueStmt):
            # не проверяем наличие цикла для MVP
            continue

        elif isinstance(s, ReturnStmt):
            if not allow_top_level and expected_return_type is None:
                # In function context, expected_return_type is None, so allow but infer observed type
                pass
            observed = None
            if s.value is not None:
                observed = _infer_expr_type(s.value, env, functions, ret_types, expected=expected_return_type, input_types=input_types, classes=classes)
            if observed_return_type is None:
                observed_return_type = observed
            else:
                observed_return_type = _merge_return_types(observed_return_type, observed)  # type: ignore[arg-type]

        elif isinstance(s, ExprStmt):
            _infer_expr_type(s.expr, env, functions, ret_types, expected=None, input_types=input_types, classes=classes)

        else:
            # Shouldn't happen for MVP
            raise TILCompileError("Ката: непредвиденный оператор.", s.loc.line, s.loc.column)

    return observed_return_type


def _analyze_for(s: ForStmt, env: list[dict[str, Type]], functions: dict[str, FunctionDef], ret_types: dict[str, Type], input_types: dict[tuple[int, int], Type] | None = None, classes: dict[str, ClassDef] | None = None) -> None:
    # init
    if isinstance(s.init, VarDecl):
        _declare(env, s.init.name, s.init.var_type, s.init.loc)
        if s.init.init is not None:
            _infer_expr_type(s.init.init, env, functions, ret_types, expected=s.init.var_type, input_types=input_types, classes=classes)
    else:
        _check_assign(s.init, env, functions, ret_types, input_types, classes)  # type: ignore[arg-type]

    cond_t = _infer_expr_type(s.cond, env, functions, ret_types, expected=Type.from_name("логикалык"), input_types=input_types, classes=classes)
    if cond_t.kind != TypeKind.BOOL and cond_t.kind != TypeKind.UNKNOWN:
        raise TILCompileError("Ката: условие 'үчүн' должно быть логическим.", s.loc.line, s.loc.column)

    if isinstance(s.step, Assign):
        _check_assign(s.step, env, functions, ret_types, input_types, classes)
    elif isinstance(s.step, AssignOp):
        _check_assign_op(s.step, env, functions, ret_types, input_types, classes)
    else:
        raise TILCompileError("Ката: step үчүн Assign же AssignOp керек.", s.loc.line, s.loc.column)

    _analyze_statements(s.body, env, functions, ret_types, expected_return_type=None, input_types=input_types, classes=classes)


def _check_assign(a: Assign, env: list[dict[str, Type]], functions: dict[str, FunctionDef], ret_types: dict[str, Type], input_types: dict[tuple[int, int], Type] | None = None, classes: dict[str, ClassDef] | None = None) -> None:
    if isinstance(a.target, VarRef):
        t = _lookup(env, a.target.name)
        if t is None:
            raise TILCompileError(f"Ката: переменная '{a.target.name}' аныкталган эмес.", a.loc.line, a.loc.column)
        _infer_expr_type(a.value, env, functions, ret_types, expected=t, input_types=input_types, classes=classes)
        return

    if isinstance(a.target, DotRef):
        obj_t = _infer_expr_type(a.target.obj, env, functions, ret_types, expected=None, input_types=input_types, classes=classes)
        if obj_t.kind != TypeKind.CLASS or not classes or obj_t.class_name not in classes:
            raise TILCompileError("Ката: талаага жазуу үчүн класс керек.", a.loc.line, a.loc.column)
        cls = classes[obj_t.class_name]
        field_t = next((ft for ft, fn in cls.fields if fn == a.target.field), None)
        if field_t is None:
            raise TILCompileError(f"Ката: '{a.target.field}' талаасы табылган жок.", a.loc.line, a.loc.column)
        _infer_expr_type(a.value, env, functions, ret_types, expected=field_t, input_types=input_types, classes=classes)
        return

    if isinstance(a.target, IndexRef):
        arr_t = _lookup(env, a.target.array.name)
        if arr_t is None:
            raise TILCompileError(f"Ката: массив '{a.target.array.name}' аныкталган эмес.", a.loc.line, a.loc.column)
        if arr_t.kind != TypeKind.LIST:
            raise TILCompileError("Ката: индекс коюуга тек массив колдонулат.", a.loc.line, a.loc.column)
        idx_t = _infer_expr_type(a.target.index, env, functions, ret_types, expected=Type.from_name("бүтүн"), input_types=input_types, classes=classes)
        if idx_t.kind != TypeKind.INT and idx_t.kind != TypeKind.UNKNOWN:
            raise TILCompileError("Ката: массив индекси бүтүн болуш керек.", a.loc.line, a.loc.column)
        item_t = arr_t.item or Type.unknown()
        _infer_expr_type(a.value, env, functions, ret_types, expected=item_t, input_types=input_types, classes=classes)
        return

    raise TILCompileError("Ката: левосторонняя часть присваивания не поддерживается.", a.loc.line, a.loc.column)


def _check_assign_op(a: AssignOp, env: list[dict[str, Type]], functions: dict[str, FunctionDef], ret_types: dict[str, Type], input_types: dict[tuple[int, int], Type] | None = None, classes: dict[str, ClassDef] | None = None) -> None:
    """x += y: target must be numeric (or string for +=), value must match."""
    if isinstance(a.target, VarRef):
        t = _lookup(env, a.target.name)
        if t is None:
            raise TILCompileError(f"Ката: переменная '{a.target.name}' аныкталган эмес.", a.loc.line, a.loc.column)
        if a.op == "+=":
            if t.kind == TypeKind.STRING:
                _infer_expr_type(a.value, env, functions, ret_types, expected=t, input_types=input_types)
                return
            if t.kind in {TypeKind.INT, TypeKind.FLOAT, TypeKind.UNKNOWN}:
                _infer_expr_type(a.value, env, functions, ret_types, expected=t, input_types=input_types)
                return
            raise TILCompileError("Ката: '+=' сап же сан үчүн гана.", a.loc.line, a.loc.column)
        if a.op in {"-=", "*=", "/=", "%="}:
            if t.kind not in {TypeKind.INT, TypeKind.FLOAT, TypeKind.UNKNOWN}:
                raise TILCompileError("Ката: -=, *=, /=, %= сандар үчүн гана.", a.loc.line, a.loc.column)
            if a.op == "%=" and t.kind == TypeKind.FLOAT:
                raise TILCompileError("Ката: '%=' тек бүтүн үчүн.", a.loc.line, a.loc.column)
            _infer_expr_type(a.value, env, functions, ret_types, expected=t, input_types=input_types, classes=classes)
            return

    if isinstance(a.target, IndexRef):
        arr_t = _lookup(env, a.target.array.name)
        if arr_t is None or arr_t.kind != TypeKind.LIST or arr_t.item is None:
            raise TILCompileError("Ката: массив аныкталган эмес.", a.loc.line, a.loc.column)
        item_t = arr_t.item
        _infer_expr_type(a.target.index, env, functions, ret_types, expected=Type.from_name("бүтүн"), input_types=input_types, classes=classes)
        if a.op == "+=":
            if item_t.kind == TypeKind.STRING:
                _infer_expr_type(a.value, env, functions, ret_types, expected=item_t, input_types=input_types, classes=classes)
                return
            if item_t.kind in {TypeKind.INT, TypeKind.FLOAT, TypeKind.UNKNOWN}:
                _infer_expr_type(a.value, env, functions, ret_types, expected=item_t, input_types=input_types, classes=classes)
                return
        if a.op in {"-=", "*=", "/=", "%="}:
            if item_t.kind not in {TypeKind.INT, TypeKind.FLOAT, TypeKind.UNKNOWN}:
                raise TILCompileError("Ката: -=, *=, /=, %= сандар үчүн гана.", a.loc.line, a.loc.column)
        _infer_expr_type(a.value, env, functions, ret_types, expected=item_t, input_types=input_types, classes=classes)
        return

    if isinstance(a.target, DotRef):
        obj_t = _infer_expr_type(a.target.obj, env, functions, ret_types, expected=None, input_types=input_types, classes=classes)
        if obj_t.kind != TypeKind.CLASS or not classes or obj_t.class_name not in classes:
            raise TILCompileError("Ката: AssignOp класс талаасы үчүн гана.", a.loc.line, a.loc.column)
        cls = classes[obj_t.class_name]
        field_t = next((ft for ft, fn in cls.fields if fn == a.target.field), None)
        if field_t is None:
            raise TILCompileError(f"Ката: '{a.target.field}' талаасы табылган жок.", a.loc.line, a.loc.column)
        if a.op not in {"+=", "-=", "*=", "/=", "%="}:
            raise TILCompileError("Ката: AssignOp талаа үчүн колдонулбайт.", a.loc.line, a.loc.column)
        _infer_expr_type(a.value, env, functions, ret_types, expected=field_t, input_types=input_types, classes=classes)
        return

    raise TILCompileError("Ката: AssignOp үчүн туура эмес цель.", a.loc.line, a.loc.column)


def _infer_expr_type(
    e: object,
    env: list[dict[str, Type]],
    functions: dict[str, FunctionDef],
    ret_types: dict[str, Type],
    expected: Type | None,
    input_types: dict[tuple[int, int], Type] | None = None,
    classes: dict[str, ClassDef] | None = None,
) -> Type:
    # Семантика MVP: вычисляем тип выражения и затем, если задан expected,
    # проверяем совместимость (с учетом допустимых приведений).
    if isinstance(e, Literal):
        t = e.value_type
        return _check_expected_compat(t, expected, e.loc)

    if isinstance(e, VarRef):
        t = _lookup(env, e.name)
        if t is None:
            raise TILCompileError(f"Ката: переменная '{e.name}' аныкталган эмес.", e.loc.line, e.loc.column)
        return _check_expected_compat(t, expected, e.loc)

    if isinstance(e, InputExpr):
        # окуу() возвращает строку. Дальше семантика должна привести к ожидаемому типу.
        if expected is None:
            # allow unknown context
            return _check_expected_compat(Type.from_name("сап"), None, e.loc)
        _check_cast_possible(Type.from_name("сап"), expected, e.loc)
        if input_types is not None:
            input_types[(e.loc.line, e.loc.column)] = expected
        return _check_expected_compat(expected, expected, e.loc)

    if isinstance(e, CastExpr):
        src_t = _infer_expr_type(e.expr, env, functions, ret_types, expected=None, input_types=input_types, classes=classes)
        _check_cast_possible(src_t, e.target_type, e.loc)
        return _check_expected_compat(e.target_type, expected, e.loc)

    if isinstance(e, ArrayLiteral):
        if not e.items:
            # empty []: need explicit expected type: тизме<бүтүн> a = [];
            if expected is None or expected.kind != TypeKind.LIST or expected.item is None:
                raise TILCompileError("Ката: бош [] үчүн тизме<тип> керек.", e.loc.line, e.loc.column)
            return _check_expected_compat(expected, expected, e.loc)
        # with items: use expected.item if provided, else infer from elements
        if expected is not None and expected.kind == TypeKind.LIST and expected.item is not None:
            item_t = expected.item
        else:
            item_t = _infer_expr_type(e.items[0], env, functions, ret_types, expected=None, input_types=input_types, classes=classes)
            for it in e.items[1:]:
                t = _infer_expr_type(it, env, functions, ret_types, expected=None, input_types=input_types, classes=classes)
                if is_numeric(item_t) and is_numeric(t):
                    item_t = promote_numeric(item_t, t)
        for it in e.items:
            _infer_expr_type(it, env, functions, ret_types, expected=item_t, input_types=input_types, classes=classes)
        return _check_expected_compat(Type.list_of(item_t), expected, e.loc)

    if isinstance(e, DotExpr):
        obj_t = _infer_expr_type(e.obj, env, functions, ret_types, expected=None, input_types=input_types, classes=classes)
        if obj_t.kind != TypeKind.CLASS or not classes or obj_t.class_name not in classes:
            raise TILCompileError("Ката: талаага кирүү үчүн класс керек.", e.loc.line, e.loc.column)
        cls = classes[obj_t.class_name]
        field_t = next((ft for ft, fn in cls.fields if fn == e.field), None)
        if field_t is None:
            raise TILCompileError(f"Ката: '{e.field}' талаасы табылган жок.", e.loc.line, e.loc.column)
        return _check_expected_compat(field_t, expected, e.loc)

    if isinstance(e, IndexExpr):
        arr_t = _infer_expr_type(e.array, env, functions, ret_types, expected=None, input_types=input_types, classes=classes)
        if arr_t.kind != TypeKind.LIST or arr_t.item is None:
            raise TILCompileError("Ката: индексация тек массивке болуш керек.", e.loc.line, e.loc.column)
        idx_t = _infer_expr_type(e.index, env, functions, ret_types, expected=Type.from_name("бүтүн"), input_types=input_types, classes=classes)
        if idx_t.kind != TypeKind.INT and idx_t.kind != TypeKind.UNKNOWN:
            raise TILCompileError("Ката: массив индекси бүтүн болуш керек.", e.loc.line, e.loc.column)
        return _check_expected_compat(arr_t.item, expected, e.loc)

    if isinstance(e, IncDecExpr):
        if isinstance(e.target, VarRef):
            t = _lookup(env, e.target.name)
        else:
            arr_t = _lookup(env, e.target.array.name)
            if arr_t is None or arr_t.kind != TypeKind.LIST or arr_t.item is None:
                raise TILCompileError("Ката: ++/-- массив элементи үчүн гана.", e.loc.line, e.loc.column)
            _infer_expr_type(e.target.index, env, functions, ret_types, expected=Type.from_name("бүтүн"), input_types=input_types, classes=classes)
            t = arr_t.item
        if t is None:
            raise TILCompileError("Ката: ++/-- үчүн аныкталган эмес өзгөрмө.", e.loc.line, e.loc.column)
        if t.kind not in {TypeKind.INT, TypeKind.FLOAT, TypeKind.UNKNOWN}:
            raise TILCompileError("Ката: ++/-- сан үчүн гана (бүтүн, чыныгы).", e.loc.line, e.loc.column)
        return _check_expected_compat(t, expected, e.loc)

    if isinstance(e, UnaryOp):
        right_t = _infer_expr_type(e.right, env, functions, ret_types, expected=None, input_types=input_types)
        if e.op == "-":
            if right_t.kind not in {TypeKind.INT, TypeKind.FLOAT, TypeKind.UNKNOWN}:
                raise TILCompileError("Ката: унар '-‘ сан үчүн гана иштейт.", e.loc.line, e.loc.column)
            return _check_expected_compat(right_t, expected, e.loc)
        if e.op == "!":
            if right_t.kind != TypeKind.BOOL and right_t.kind != TypeKind.UNKNOWN:
                raise TILCompileError("Ката: унар 'эмес' логикалык үчүн гана иштейт.", e.loc.line, e.loc.column)
            return _check_expected_compat(Type.from_name("логикалык"), expected, e.loc)
        raise TILCompileError("Ката: белгисиз унар операция.", e.loc.line, e.loc.column)

    if isinstance(e, BinOp):
        lt = _infer_expr_type(e.left, env, functions, ret_types, expected=None, input_types=input_types, classes=classes)
        rt = _infer_expr_type(e.right, env, functions, ret_types, expected=None, input_types=input_types, classes=classes)
        op = e.op

        if op in {"+", "-", "*", "/", "%"}:
            # During recursion or multi-pass inference, operand types might be UNKNOWN.
            # For MVP we allow UNKNOWN to participate in numeric expressions.
            if op == "%":
                if lt.kind not in {TypeKind.INT, TypeKind.UNKNOWN} or rt.kind not in {TypeKind.INT, TypeKind.UNKNOWN}:
                    raise TILCompileError("Ката: '%' тек бүтүн сандар үчүн колдонулат.", e.loc.line, e.loc.column)
                # If both known -> int, otherwise keep unknown.
                t = Type.from_name("бүтүн") if lt.kind == TypeKind.INT and rt.kind == TypeKind.INT else Type.unknown()
                return _check_expected_compat(t, expected, e.loc)

            if lt.kind not in {TypeKind.INT, TypeKind.FLOAT, TypeKind.UNKNOWN} or rt.kind not in {TypeKind.INT, TypeKind.FLOAT, TypeKind.UNKNOWN}:
                raise TILCompileError("Ката: арифметикалык операция сандар үчүн гана иштейт.", e.loc.line, e.loc.column)

            # numeric promotion: if both known -> promote, otherwise keep known/unknown.
            if lt.kind == TypeKind.UNKNOWN or rt.kind == TypeKind.UNKNOWN:
                # If one side is known numeric, the other is unknown: result is unknown for safety.
                t = Type.unknown()
            else:
                t = promote_numeric(lt, rt)
            return _check_expected_compat(t, expected, e.loc)

        if op in {"&&", "||"}:
            if (lt.kind != TypeKind.BOOL and lt.kind != TypeKind.UNKNOWN) or (rt.kind != TypeKind.BOOL and rt.kind != TypeKind.UNKNOWN):
                raise TILCompileError("Ката: логикалык операциялар логикалык маанилер менен иштейт.", e.loc.line, e.loc.column)
            t = Type.from_name("логикалык")
            return _check_expected_compat(t, expected, e.loc)

        if op in {"==", "!="}:
            if lt.kind == rt.kind:
                return _check_expected_compat(Type.from_name("логикалык"), expected, e.loc)
            if (is_numeric(lt) and is_numeric(rt)) or lt.kind == TypeKind.UNKNOWN or rt.kind == TypeKind.UNKNOWN:
                return _check_expected_compat(Type.from_name("логикалык"), expected, e.loc)
            # Allow char<->string comparisons by coercion in runtime? We'll keep strict.
            raise TILCompileError("Ката: салыштыруу түрлөрү дал келбейт.", e.loc.line, e.loc.column)

        if op in {">", ">=", "<", "<="}:
            if (is_numeric(lt) and is_numeric(rt)) or lt.kind == TypeKind.UNKNOWN or rt.kind == TypeKind.UNKNOWN:
                return _check_expected_compat(Type.from_name("логикалык"), expected, e.loc)
            if (lt.kind in {TypeKind.STRING, TypeKind.CHAR} and rt.kind in {TypeKind.STRING, TypeKind.CHAR}) or lt.kind == TypeKind.UNKNOWN or rt.kind == TypeKind.UNKNOWN:
                return _check_expected_compat(Type.from_name("логикалык"), expected, e.loc)
            raise TILCompileError("Ката: бул салыштыруу үчүн түрлөр туура эмес.", e.loc.line, e.loc.column)

        raise TILCompileError("Ката: белгисиз бинар операция.", e.loc.line, e.loc.column)

    if isinstance(e, CallExpr):
        # Builtins
        if e.name == BUILTIN_INPUT:
            raise TILCompileError("Ката: 'окуу()' башкача формада колдонулду.", e.loc.line, e.loc.column)
        if e.name == BUILTIN_LENGTH:
            if len(e.args) != 1:
                raise TILCompileError("Ката: узундук() бир аргумент алат.", e.loc.line, e.loc.column)
            a_t = _infer_expr_type(e.args[0], env, functions, ret_types, expected=None, input_types=input_types, classes=classes)
            if a_t.kind not in {TypeKind.STRING, TypeKind.LIST}:
                raise TILCompileError("Ката: узундук() тек сап же тизме менен иштейт.", e.loc.line, e.loc.column)
            return _check_expected_compat(Type.from_name("бүтүн"), expected, e.loc)
        if e.name == BUILTIN_PRINT:
            if len(e.args) != 1:
                raise TILCompileError("Ката: чыгар() бир аргумент алат.", e.loc.line, e.loc.column)
            _infer_expr_type(e.args[0], env, functions, ret_types, expected=None, input_types=input_types, classes=classes)
            return _check_expected_compat(Type.void(), expected, e.loc)

        # User-defined functions
        fn = functions.get(e.name)
        if fn is None:
            raise TILCompileError(f"Ката: '{e.name}' функциясы табылган жок.", e.loc.line, e.loc.column)
        if len(e.args) != len(fn.params):
            raise TILCompileError("Ката: функция аргументтеринин саны дал келбейт.", e.loc.line, e.loc.column)
        for (p_type, _p_name), arg in zip(fn.params, e.args):
            _infer_expr_type(arg, env, functions, ret_types, expected=p_type, input_types=input_types, classes=classes)
        t = ret_types.get(e.name, Type.unknown())
        return _check_expected_compat(t, expected, e.loc)

    raise TILCompileError("Ката: белгисиз туюнтма.", getattr(e, "loc", NodeLoc(0, 0)).line, getattr(e, "loc", NodeLoc(0, 0)).column)


def _check_expected_compat(actual: Type, expected: Type | None, loc: NodeLoc) -> Type:
    if expected is None:
        return actual
    if expected.kind == TypeKind.UNKNOWN or actual.kind == TypeKind.UNKNOWN:
        return actual
    if types_equal(actual, expected):
        return actual
    # Разрешаем числовые преобразования.
    if is_numeric(actual) and is_numeric(expected):
        return expected
    _check_cast_possible(actual, expected, loc)
    return expected


def _check_cast_possible(src: Type, dst: Type, loc: NodeLoc) -> None:
    if dst.kind == TypeKind.UNKNOWN:
        return
    if src.kind == dst.kind:
        return
    # Primitives -> string: needed for `сап s = "..."; s += x;`
    if dst.kind == TypeKind.STRING and src.kind in {TypeKind.INT, TypeKind.FLOAT, TypeKind.BOOL, TypeKind.CHAR, TypeKind.LIST}:
        return
    # Input is string. Allow conversion from string to primitives and list (split at runtime).
    if src.kind == TypeKind.STRING:
        if dst.kind in {TypeKind.INT, TypeKind.FLOAT, TypeKind.BOOL, TypeKind.CHAR}:
            return
        if dst.kind == TypeKind.LIST:
            return  # окуу() for list: split line by whitespace, cast elements
    # Numeric promotion
    if is_numeric(src) and is_numeric(dst):
        return
    # Prevent int<->bool, string<->numeric etc for MVP
    raise TILCompileError(f"Ката: '{src}' маанисин '{dst}' түрүнө айлантуу мүмкүн эмес.", loc.line, loc.column)

