from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TokenType(str, Enum):
    # Single char / delimiters
    LPAREN = "("
    RPAREN = ")"
    LBRACE = "{"
    RBRACE = "}"
    LBRACKET = "["
    RBRACKET = "]"
    COMMA = ","
    SEMI = ";"
    DOT = "."

    # Operators
    PLUS = "+"
    MINUS = "-"
    STAR = "*"
    SLASH = "/"
    PERCENT = "%"

    ASSIGN = "="
    EQ = "=="
    NEQ = "!="
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="

    AND = "&&"
    OR = "||"
    NOT = "!"

    # Shorthand / C++-style
    INC = "++"
    DEC = "--"
    PLUSEQ = "+="
    MINUSEQ = "-="
    STAREQ = "*="
    SLASHEQ = "/="
    PERCENTEQ = "%="

    # Identifiers / literals
    IDENT = "IDENT"
    INT = "INT"
    FLOAT = "FLOAT"
    STRING = "STRING"
    CHAR = "CHAR"

    # Keywords (Кыргызстанский MVP)
    CLASS = "класс"
    FUNC = "функция"
    IF = "эгер"
    ELSE = "болбосо"
    WHILE = "качан"
    DO = "жаса"
    FOR = "үчүн"
    BREAK = "токтот"
    CONTINUE = "улантуу"
    RETURN = "кайтар"

    TRUE = "чын"
    FALSE = "жалган"

    TYPE_INT = "бүтүн"
    TYPE_FLOAT = "чыныгы"
    TYPE_STRING = "сап"
    TYPE_CHAR = "белги"
    TYPE_BOOL = "логикалык"
    TYPE_LIST = "тизме"

    # Logical text aliases (обрабатываются как AND/OR/NOT на этапе лексера)
    AND_WORD = "жана"
    OR_WORD = "же"
    NOT_WORD = "эмес"

    # Builtins
    PRINT = "чыгар"
    INPUT = "окуу"
    LENGTH = "узундук"

    END = "END"


@dataclass(frozen=True)
class Token:
    type: TokenType
    value: str
    line: int
    column: int

