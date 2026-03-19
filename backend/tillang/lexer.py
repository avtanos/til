from __future__ import annotations

from dataclasses import dataclass

from .errors import TILCompileError
from .tokens import Token, TokenType


KEYWORDS: dict[str, TokenType] = {
    TokenType.FUNC.value: TokenType.FUNC,
    TokenType.IF.value: TokenType.IF,
    TokenType.ELSE.value: TokenType.ELSE,
    TokenType.WHILE.value: TokenType.WHILE,
    TokenType.DO.value: TokenType.DO,
    TokenType.FOR.value: TokenType.FOR,
    TokenType.BREAK.value: TokenType.BREAK,
    TokenType.CONTINUE.value: TokenType.CONTINUE,
    TokenType.RETURN.value: TokenType.RETURN,
    TokenType.TRUE.value: TokenType.TRUE,
    TokenType.FALSE.value: TokenType.FALSE,
    TokenType.TYPE_INT.value: TokenType.TYPE_INT,
    TokenType.TYPE_FLOAT.value: TokenType.TYPE_FLOAT,
    TokenType.TYPE_STRING.value: TokenType.TYPE_STRING,
    TokenType.TYPE_CHAR.value: TokenType.TYPE_CHAR,
    TokenType.TYPE_BOOL.value: TokenType.TYPE_BOOL,
    TokenType.TYPE_LIST.value: TokenType.TYPE_LIST,
    TokenType.AND_WORD.value: TokenType.AND,
    TokenType.OR_WORD.value: TokenType.OR,
    TokenType.NOT_WORD.value: TokenType.NOT,
    TokenType.PRINT.value: TokenType.PRINT,
    TokenType.INPUT.value: TokenType.INPUT,
    TokenType.LENGTH.value: TokenType.LENGTH,
}


@dataclass
class LexerState:
    src: str
    i: int = 0
    line: int = 1
    col: int = 1

    def peek(self, k: int = 0) -> str:
        j = self.i + k
        if j >= len(self.src):
            return ""
        return self.src[j]

    def advance(self, n: int = 1) -> None:
        for _ in range(n):
            if self.i >= len(self.src):
                return
            ch = self.src[self.i]
            self.i += 1
            if ch == "\n":
                self.line += 1
                self.col = 1
            else:
                self.col += 1


def _is_ident_start(ch: str) -> bool:
    if not ch:
        return False
    # Cyrillic letters + underscore
    return ch == "_" or ch.isalpha() or (ch >= "А" and ch <= "я") or (ch >= "Ѐ" and ch <= "ӿ")


def _is_ident_part(ch: str) -> bool:
    return _is_ident_start(ch) or ch.isdigit()


def tokenize(src: str) -> list[Token]:
    st = LexerState(src=src)
    tokens: list[Token] = []

    def add(tt: TokenType, val: str, line: int, col: int) -> None:
        tokens.append(Token(type=tt, value=val, line=line, column=col))

    while True:
        ch = st.peek()
        if ch == "":
            tokens.append(Token(TokenType.END, "", st.line, st.col))
            return tokens

        # whitespace
        if ch.isspace():
            st.advance()
            continue

        # comments: //...
        if ch == "/" and st.peek(1) == "/":
            while st.peek() not in {"", "\n"}:
                st.advance()
            continue
        # comments: /* ... */
        if ch == "/" and st.peek(1) == "*":
            start_line, start_col = st.line, st.col
            st.advance(2)
            while True:
                if st.peek() == "":
                    raise TILCompileError("Коментарий не закрыт.", start_line, start_col)
                if st.peek() == "*" and st.peek(1) == "/":
                    st.advance(2)
                    break
                st.advance()
            continue

        # multi-char operators
        line, col = st.line, st.col
        two = ch + st.peek(1)
        if two == "==":
            add(TokenType.EQ, "==", line, col)
            st.advance(2)
            continue
        if two == "!=":
            add(TokenType.NEQ, "!=", line, col)
            st.advance(2)
            continue
        if two == ">=":
            add(TokenType.GTE, ">=", line, col)
            st.advance(2)
            continue
        if two == "<=":
            add(TokenType.LTE, "<=", line, col)
            st.advance(2)
            continue
        if two == "&&":
            add(TokenType.AND, "&&", line, col)
            st.advance(2)
            continue
        if two == "||":
            add(TokenType.OR, "||", line, col)
            st.advance(2)
            continue

        # single char tokens
        single_map = {
            "(": TokenType.LPAREN,
            ")": TokenType.RPAREN,
            "{": TokenType.LBRACE,
            "}": TokenType.RBRACE,
            "[": TokenType.LBRACKET,
            "]": TokenType.RBRACKET,
            ",": TokenType.COMMA,
            ";": TokenType.SEMI,
            "+": TokenType.PLUS,
            "-": TokenType.MINUS,
            "*": TokenType.STAR,
            "/": TokenType.SLASH,
            "%": TokenType.PERCENT,
            "=": TokenType.ASSIGN,
            ">": TokenType.GT,
            "<": TokenType.LT,
            "!": TokenType.NOT,
        }
        if ch in single_map:
            add(single_map[ch], ch, line, col)
            st.advance()
            continue

        # string literals
        if ch == '"' or ch == "'":
            quote = ch
            st.advance()
            start_line, start_col = line, col
            out = []
            while True:
                c = st.peek()
                if c == "":
                    raise TILCompileError("Строка не закрыта.", start_line, start_col)
                if c == "\n":
                    raise TILCompileError("Строка не может содержать перевод строки.", start_line, start_col)
                if c == quote:
                    st.advance()
                    break
                if c == "\\":
                    st.advance()
                    esc = st.peek()
                    if esc == "":
                        raise TILCompileError("Незавершенная escape-последовательность.", start_line, start_col)
                    mapping = {
                        "n": "\n",
                        "t": "\t",
                        '"': '"',
                        "'": "'",
                        "\\": "\\",
                    }
                    out.append(mapping.get(esc, esc))
                    st.advance()
                else:
                    out.append(c)
                    st.advance()
            text = "".join(out)
            tt = TokenType.STRING if quote == '"' else TokenType.CHAR
            add(tt, text, line, col)
            continue

        # numbers
        if ch.isdigit():
            start_line, start_col = line, col
            num = []
            has_dot = False
            while True:
                c = st.peek()
                if c == "." and not has_dot:
                    has_dot = True
                    num.append(c)
                    st.advance()
                    continue
                if c.isdigit():
                    num.append(c)
                    st.advance()
                    continue
                break
            text = "".join(num)
            add(TokenType.FLOAT if has_dot else TokenType.INT, text, start_line, start_col)
            continue

        # identifiers / keywords
        if _is_ident_start(ch):
            start_line, start_col = line, col
            ident = []
            while _is_ident_part(st.peek()):
                ident.append(st.peek())
                st.advance()
            name = "".join(ident)
            tt = KEYWORDS.get(name, TokenType.IDENT)
            add(tt, name, start_line, start_col)
            continue

        raise TILCompileError(f"Непонятный символ: {ch!r}.", line, col)

