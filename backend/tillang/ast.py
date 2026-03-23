from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .typesys import Type


@dataclass(frozen=True, slots=True)
class NodeLoc:
    line: int
    column: int


class Expr:
    loc: NodeLoc


class Stmt:
    loc: NodeLoc


@dataclass(frozen=True, slots=True)
class Program:
    classes: list["ClassDef"]
    functions: list["FunctionDef"]
    main_stmts: list[Stmt]


@dataclass(frozen=True, slots=True)
class ClassDef:
    name: str
    fields: list[tuple[Type, str]]  # (type, name)
    loc: NodeLoc


@dataclass(frozen=True, slots=True)
class FunctionDef:
    name: str
    params: list[tuple[Type, str]]
    body: list[Stmt]
    loc: NodeLoc


@dataclass(frozen=True, slots=True)
class Block:
    stmts: list[Stmt]
    loc: NodeLoc


@dataclass(frozen=True, slots=True)
class VarDecl(Stmt):
    var_type: Type
    name: str
    init: Expr | None
    loc: NodeLoc


@dataclass(frozen=True, slots=True)
class Assign(Stmt):
    target: "LValue"
    value: Expr
    loc: NodeLoc


@dataclass(frozen=True, slots=True)
class AssignOp(Stmt):
    """x += y, x -= y, etc."""
    target: "LValue"
    op: str  # +=, -=, *=, /=, %=
    value: Expr
    loc: NodeLoc


class LValue:
    loc: NodeLoc


@dataclass(frozen=True, slots=True)
class VarRef(Expr, LValue):
    name: str
    loc: NodeLoc


@dataclass(frozen=True, slots=True)
class IndexRef(LValue):
    array: VarRef
    index: Expr
    loc: NodeLoc


@dataclass(frozen=True, slots=True)
class DotRef(LValue):
    """obj.field for assignment"""
    obj: Expr
    field: str
    loc: NodeLoc


@dataclass(frozen=True, slots=True)
class IfStmt(Stmt):
    cond: Expr
    then_body: list[Stmt]
    else_body: list[Stmt] | None
    loc: NodeLoc


@dataclass(frozen=True, slots=True)
class WhileStmt(Stmt):
    cond: Expr
    body: list[Stmt]
    loc: NodeLoc


@dataclass(frozen=True, slots=True)
class ForStmt(Stmt):
    init: Stmt  # VarDecl or Assign
    cond: Expr
    step: Stmt  # Assign or AssignOp
    body: list[Stmt]
    loc: NodeLoc


@dataclass(frozen=True, slots=True)
class DoWhileStmt(Stmt):
    body: list[Stmt]
    cond: Expr
    loc: NodeLoc


@dataclass(frozen=True, slots=True)
class BreakStmt(Stmt):
    loc: NodeLoc


@dataclass(frozen=True, slots=True)
class ContinueStmt(Stmt):
    loc: NodeLoc


@dataclass(frozen=True, slots=True)
class ReturnStmt(Stmt):
    value: Expr | None
    loc: NodeLoc


@dataclass(frozen=True, slots=True)
class ExprStmt(Stmt):
    expr: Expr
    loc: NodeLoc


@dataclass(frozen=True, slots=True)
class Literal(Expr):
    value: Any
    value_type: Type
    loc: NodeLoc


@dataclass(frozen=True, slots=True)
class UnaryOp(Expr):
    op: str
    right: Expr
    loc: NodeLoc


@dataclass(frozen=True, slots=True)
class IncDecExpr(Expr):
    """++i, i++, --i, i--"""
    op: str  # "++" or "--"
    target: "LValue"
    is_postfix: bool  # True for i++, False for ++i
    loc: NodeLoc


@dataclass(frozen=True, slots=True)
class BinOp(Expr):
    op: str
    left: Expr
    right: Expr
    loc: NodeLoc


@dataclass(frozen=True, slots=True)
class CastExpr(Expr):
    expr: Expr
    target_type: Type
    loc: NodeLoc


@dataclass(frozen=True, slots=True)
class CallExpr(Expr):
    name: str
    args: list[Expr]
    loc: NodeLoc


@dataclass(frozen=True, slots=True)
class ArrayLiteral(Expr):
    item_type: Type
    items: list[Expr]
    loc: NodeLoc


@dataclass(frozen=True, slots=True)
class IndexExpr(Expr):
    array: Expr  # typically VarRef
    index: Expr
    loc: NodeLoc


@dataclass(frozen=True, slots=True)
class DotExpr(Expr):
    """obj.field for reading"""
    obj: Expr
    field: str
    loc: NodeLoc


@dataclass(frozen=True, slots=True)
class LengthExpr(Expr):
    target: Expr
    loc: NodeLoc


@dataclass(frozen=True, slots=True)
class InputExpr(Expr):
    loc: NodeLoc

