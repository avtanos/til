from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TypeKind(str, Enum):
    INT = "бүтүн"
    FLOAT = "чыныгы"
    STRING = "сап"
    CHAR = "белги"
    BOOL = "логикалык"
    LIST = "тизме"
    VOID = "VOID"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class Type:
    kind: TypeKind
    item: "Type | None" = None  # for LIST

    def __str__(self) -> str:
        if self.kind == TypeKind.LIST and self.item is not None:
            return f"тизме<{self.item}>"
        return self.kind.value

    @staticmethod
    def from_name(name: str) -> "Type":
        m = {
            "бүтүн": TypeKind.INT,
            "чыныгы": TypeKind.FLOAT,
            "сап": TypeKind.STRING,
            "белги": TypeKind.CHAR,
            "логикалык": TypeKind.BOOL,
            "тизме": TypeKind.LIST,
        }
        return Type(kind=m.get(name, TypeKind.UNKNOWN))

    @staticmethod
    def list_of(item: "Type") -> "Type":
        return Type(kind=TypeKind.LIST, item=item)

    @staticmethod
    def void() -> "Type":
        return Type(kind=TypeKind.VOID)

    @staticmethod
    def unknown() -> "Type":
        return Type(kind=TypeKind.UNKNOWN)


def is_numeric(t: Type) -> bool:
    return t.kind in {TypeKind.INT, TypeKind.FLOAT}


def promote_numeric(a: Type, b: Type) -> Type:
    # int + float => float, float + int => float
    if a.kind == TypeKind.FLOAT or b.kind == TypeKind.FLOAT:
        return Type(kind=TypeKind.FLOAT)
    return Type(kind=TypeKind.INT)


def types_equal(a: Type, b: Type) -> bool:
    if a.kind != b.kind:
        return False
    if a.kind == TypeKind.LIST:
        return a.item == b.item
    return True

