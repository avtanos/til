from __future__ import annotations

from dataclasses import dataclass

from .ast import (
    ArrayLiteral,
    Assign,
    AssignOp,
    BinOp,
    Block,
    CallExpr,
    CastExpr,
    ClassDef,
    DoWhileStmt,
    DotExpr,
    DotRef,
    ExprStmt,
    ForStmt,
    FunctionDef,
    IncDecExpr,
    IndexExpr,
    IndexRef,
    IfStmt,
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
    BreakStmt,
    ContinueStmt,
)
from .errors import TILCompileError
from .lexer import tokenize
from .tokens import Token, TokenType
from .typesys import Type, TypeKind


@dataclass
class ParserState:
    tokens: list[Token]
    idx: int = 0

    def peek(self, k: int = 0) -> Token:
        j = self.idx + k
        if j >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[j]

    def at_end(self) -> bool:
        return self.peek().type == TokenType.END

    def advance(self) -> Token:
        tok = self.peek()
        self.idx += 1
        return tok

    def match(self, *types: TokenType) -> Token | None:
        tok = self.peek()
        if tok.type in types:
            self.idx += 1
            return tok
        return None

    def expect(self, t: TokenType, message: str) -> Token:
        tok = self.peek()
        if tok.type != t:
            raise TILCompileError(message, tok.line, tok.column)
        self.idx += 1
        return tok


def _loc(tok: Token) -> NodeLoc:
    return NodeLoc(line=tok.line, column=tok.column)


TYPE_TOKENS = {
    TokenType.TYPE_INT,
    TokenType.TYPE_FLOAT,
    TokenType.TYPE_STRING,
    TokenType.TYPE_CHAR,
    TokenType.TYPE_BOOL,
    TokenType.TYPE_LIST,
}


def parse_type(ps: ParserState) -> Type:
    tok = ps.peek()
    if tok.type not in TYPE_TOKENS and tok.type != TokenType.IDENT:
        raise TILCompileError("Ожидалась типовая спецификация.", tok.line, tok.column)

    if tok.type == TokenType.TYPE_LIST:
        ps.advance()
        # тизме<тип>
        ps.expect(TokenType.LT, "Ожидался символ '<' после тизме.")
        item = parse_type(ps)
        ps.expect(TokenType.GT, "Ожидался символ '>' после тизме<тип>.")
        return Type.list_of(item)

    ps.advance()
    return Type.from_name(tok.value)


def parse_class(ps: ParserState) -> "ClassDef":
    ps.expect(TokenType.CLASS, "Ожидалось 'класс'.")
    name_tok = ps.expect(TokenType.IDENT, "Ожидалось имя класса.")
    ps.expect(TokenType.LBRACE, "Ожидался '{' после имени класса.")
    fields: list[tuple[Type, str]] = []
    while ps.peek().type != TokenType.RBRACE:
        if ps.at_end():
            raise TILCompileError("Класс не закрыт.", name_tok.line, name_tok.column)
        field_type = parse_type(ps)
        field_name = ps.expect(TokenType.IDENT, "Ожидалось имя поля.")
        ps.expect(TokenType.SEMI, "Ожидался ';' после поля.")
        fields.append((field_type, field_name.value))
    ps.expect(TokenType.RBRACE, "Ожидался '}' после полей класса.")
    return ClassDef(name=name_tok.value, fields=fields, loc=_loc(name_tok))


def parse(source: str) -> Program:
    tokens = tokenize(source)
    ps = ParserState(tokens=tokens)
    classes: list[ClassDef] = []
    functions: list[FunctionDef] = []
    main_stmts: list[Stmt] = []

    while not ps.at_end():
        tok = ps.peek()
        if tok.type == TokenType.CLASS:
            classes.append(parse_class(ps))
        elif tok.type == TokenType.FUNC:
            functions.append(parse_function(ps))
        elif tok.type == TokenType.IDENT and tok.value == "башкы":
            functions.append(parse_entry_function(ps))
        else:
            main_stmts.append(parse_statement(ps))

    return Program(classes=classes, functions=functions, main_stmts=main_stmts)


def parse_entry_function(ps: ParserState) -> FunctionDef:
    name_tok = ps.expect(TokenType.IDENT, "Ожидалось имя функции.")
    if name_tok.value != "башкы":
        raise AssertionError("Internal: parse_entry_function")

    ps.expect(TokenType.LPAREN, "Ожидался '(' в башкы().")
    ps.expect(TokenType.RPAREN, "Ожидался ')' в башкы().")
    body = parse_block(ps)
    return FunctionDef(name="башкы", params=[], body=body.stmts, loc=_loc(name_tok))


def parse_function(ps: ParserState) -> FunctionDef:
    ps.expect(TokenType.FUNC, "Ожидалось слово 'функция'.")
    name_tok = ps.expect(TokenType.IDENT, "Ожидалось имя функции.")
    ps.expect(TokenType.LPAREN, "Ожидался '(' после имени функции.")

    params: list[tuple[Type, str]] = []
    if ps.peek().type != TokenType.RPAREN:
        while True:
            t = parse_type(ps)
            ident_tok = ps.expect(TokenType.IDENT, "Ожидалось имя параметра.")
            params.append((t, ident_tok.value))
            if ps.match(TokenType.COMMA) is not None:
                continue
            break

    ps.expect(TokenType.RPAREN, "Ожидался ')' в объявлении функции.")
    body = parse_block(ps)
    return FunctionDef(name=name_tok.value, params=params, body=body.stmts, loc=_loc(name_tok))


def parse_block(ps: ParserState) -> Block:
    lbrace = ps.expect(TokenType.LBRACE, "Ожидался '{' для блока.")
    stmts: list[Stmt] = []
    while ps.peek().type != TokenType.RBRACE:
        if ps.at_end():
            raise TILCompileError("Блок не закрыт ('}').", lbrace.line, lbrace.column)
        stmts.append(parse_statement(ps))
    ps.expect(TokenType.RBRACE, "Ожидался '}' для закрытия блока.")
    return Block(stmts=stmts, loc=_loc(lbrace))


def parse_statement(ps: ParserState) -> Stmt:
    tok = ps.peek()

    # variable declaration: "Type Name" or "Type<...> Name" - second token is IDENT or LT (for тизме<...>)
    sec = ps.peek(1).type
    if (tok.type in TYPE_TOKENS or tok.type == TokenType.IDENT) and (sec == TokenType.IDENT or sec == TokenType.LT):
        var_type = parse_type(ps)
        name_tok = ps.expect(TokenType.IDENT, "Ожидалось имя переменной.")
        init_expr = None
        if ps.match(TokenType.ASSIGN) is not None:
            init_expr = parse_expression(ps)
        ps.expect(TokenType.SEMI, "Ожидался ';' после объявления переменной.")
        return VarDecl(var_type=var_type, name=name_tok.value, init=init_expr, loc=_loc(name_tok))

    if tok.type == TokenType.IF:
        return parse_if(ps)
    if tok.type == TokenType.WHILE:
        return parse_while(ps)
    if tok.type == TokenType.FOR:
        return parse_for(ps)
    if tok.type == TokenType.DO:
        return parse_do_while(ps)
    if tok.type == TokenType.BREAK:
        b = ps.advance()
        ps.expect(TokenType.SEMI, "Ожидался ';' после 'токтот'.")
        return BreakStmt(loc=_loc(b))
    if tok.type == TokenType.CONTINUE:
        c = ps.advance()
        ps.expect(TokenType.SEMI, "Ожидался ';' после 'улантуу'.")
        return ContinueStmt(loc=_loc(c))
    if tok.type == TokenType.RETURN:
        return parse_return(ps)

    # assignment or expression stmt
    if tok.type == TokenType.IDENT:
        # Если после IDENT стоит '(', это скорее вызов функции как выражение.
        if ps.peek(1).type == TokenType.LPAREN:
            expr = parse_expression(ps)
            ps.expect(TokenType.SEMI, "Ожидался ';' после выражения.")
            return ExprStmt(expr=expr, loc=_loc(tok))

        # Иначе пробуем распарсить lvalue и проверить '=' или +=, -=, и т.д.
        lval_start = tok
        lvalue = parse_lvalue(ps)
        assign_op_type = ps.peek().type
        if assign_op_type in ASSIGN_OPS:
            ps.advance()
            value = parse_expression(ps)
            ps.expect(TokenType.SEMI, "Ожидался ';' после присваивания.")
            return AssignOp(target=lvalue, op=ASSIGN_OPS[assign_op_type], value=value, loc=_loc(lval_start))
        if assign_op_type == TokenType.ASSIGN:
            ps.advance()  # consume '='
            value = parse_expression(ps)
            ps.expect(TokenType.SEMI, "Ожидался ';' после присваивания.")
            return Assign(target=lvalue, value=value, loc=_loc(lval_start))

        # Для MVP: standalone lvalue (без '=') в виде выражения не поддерживаем,
        # потому что это почти всегда ошибка пользователя.
        ps.expect(TokenType.SEMI, "Ожидался ';' после выражения.")
        return ExprStmt(expr=lvalue_to_expr(lvalue), loc=_loc(lval_start))

    # fallback: expression statement
    expr = parse_expression(ps)
    ps.expect(TokenType.SEMI, "Ожидался ';' после выражения.")
    return ExprStmt(expr=expr, loc=_loc(tok))


ASSIGN_OPS = {
    TokenType.PLUSEQ: "+=",
    TokenType.MINUSEQ: "-=",
    TokenType.STAREQ: "*=",
    TokenType.SLASHEQ: "/=",
    TokenType.PERCENTEQ: "%=",
}


def lvalue_to_expr(lv: "VarRef | IndexRef | DotRef"):
    if isinstance(lv, VarRef):
        return lv
    if isinstance(lv, IndexRef):
        return IndexExpr(array=lv.array, index=lv.index, loc=lv.loc)
    return DotExpr(obj=lv.obj, field=lv.field, loc=lv.loc)


def expr_to_lvalue(expr, tok_for_error) -> "VarRef | IndexRef | DotRef":
    """Convert expression to LValue; raise if not assignable."""
    if isinstance(expr, VarRef):
        return expr
    if isinstance(expr, IndexExpr) and isinstance(expr.array, VarRef):
        return IndexRef(array=expr.array, index=expr.index, loc=expr.loc)
    if isinstance(expr, DotExpr):
        return DotRef(obj=expr.obj, field=expr.field, loc=expr.loc)
    raise TILCompileError("++/-- требуют переменную, массив же талаа.", tok_for_error.line, tok_for_error.column)


def parse_return(ps: ParserState) -> ReturnStmt:
    r = ps.expect(TokenType.RETURN, "Ожидалось 'кайтар'.")
    if ps.peek().type == TokenType.SEMI:
        ps.advance()
        return ReturnStmt(value=None, loc=_loc(r))
    val = parse_expression(ps)
    ps.expect(TokenType.SEMI, "Ожидался ';' после оператора return.")
    return ReturnStmt(value=val, loc=_loc(r))


def parse_if(ps: ParserState) -> IfStmt:
    if_tok = ps.expect(TokenType.IF, "Ожидалось 'эгер'.")
    ps.expect(TokenType.LPAREN, "Ожидался '(' после 'эгер'.")
    cond = parse_expression(ps)
    ps.expect(TokenType.RPAREN, "Ожидался ')' после условия.")
    then_body = parse_block(ps).stmts
    else_body = None
    if ps.peek().type == TokenType.ELSE:
        ps.advance()
        else_body = parse_block(ps).stmts
    return IfStmt(cond=cond, then_body=then_body, else_body=else_body, loc=_loc(if_tok))


def parse_while(ps: ParserState) -> WhileStmt:
    w = ps.expect(TokenType.WHILE, "Ожидалось 'качан'.")
    ps.expect(TokenType.LPAREN, "Ожидался '(' после 'качан'.")
    cond = parse_expression(ps)
    ps.expect(TokenType.RPAREN, "Ожидался ')' после условия.")
    body = parse_block(ps).stmts
    return WhileStmt(cond=cond, body=body, loc=_loc(w))


def parse_for(ps: ParserState) -> ForStmt:
    f = ps.expect(TokenType.FOR, "Ожидалось 'үчүн'.")
    ps.expect(TokenType.LPAREN, "Ожидался '(' после 'үчүн'.")

    # init
    init: Stmt
    if ps.peek().type in TYPE_TOKENS or ps.peek().type == TokenType.IDENT:
        init_type = parse_type(ps)
        ident_tok = ps.expect(TokenType.IDENT, "Ожидалось имя переменной в init.")
        ps.expect(TokenType.ASSIGN, "Ожидался '=' в init.")
        init_val = parse_expression(ps)
        init = VarDecl(var_type=init_type, name=ident_tok.value, init=init_val, loc=_loc(ident_tok))
    else:
        lv = parse_lvalue(ps)
        ps.expect(TokenType.ASSIGN, "Ожидался '=' в init.")
        init_val = parse_expression(ps)
        init = Assign(target=lv, value=init_val, loc=lv.loc)

    ps.expect(TokenType.SEMI, "Ожидался ';' после init в for.")
    cond = parse_expression(ps)
    ps.expect(TokenType.SEMI, "Ожидался ';' после условия в for.")
    step_lv = parse_lvalue(ps)
    step_op = ps.peek().type
    if step_op in ASSIGN_OPS:
        ps.advance()
        step_val = parse_expression(ps)
        step = AssignOp(target=step_lv, op=ASSIGN_OPS[step_op], value=step_val, loc=step_lv.loc)
    else:
        ps.expect(TokenType.ASSIGN, "Ожидался '=' или +=, -= и т.д. в step.")
        step_val = parse_expression(ps)
        step = Assign(target=step_lv, value=step_val, loc=step_lv.loc)
    ps.expect(TokenType.RPAREN, "Ожидался ')' после for(...) .")
    body = parse_block(ps).stmts
    return ForStmt(init=init, cond=cond, step=step, body=body, loc=_loc(f))


def parse_do_while(ps: ParserState) -> DoWhileStmt:
    d = ps.expect(TokenType.DO, "Ожидалось 'жаса'.")
    body = parse_block(ps).stmts
    ps.expect(TokenType.WHILE, "Ожидалось слово 'качан' после do-блока.")
    ps.expect(TokenType.LPAREN, "Ожидался '(' после 'качан'.")
    cond = parse_expression(ps)
    ps.expect(TokenType.RPAREN, "Ожидался ')' после условия.")
    # semicolon is required per spec example
    ps.match(TokenType.SEMI)  # optional for robustness
    return DoWhileStmt(body=body, cond=cond, loc=_loc(d))


def parse_lvalue(ps: ParserState) -> "VarRef | IndexRef | DotRef":
    ident_tok = ps.expect(TokenType.IDENT, "Ожидалась переменная.")
    obj: Expr = VarRef(name=ident_tok.value, loc=_loc(ident_tok))
    if ps.match(TokenType.LBRACKET) is not None:
        idx_expr = parse_expression(ps)
        ps.expect(TokenType.RBRACKET, "Ожидался ']' после индекса.")
        obj = IndexExpr(array=obj, index=idx_expr, loc=obj.loc)
    if ps.match(TokenType.DOT) is not None:
        field_tok = ps.expect(TokenType.IDENT, "Ожидалось поле.")
        return DotRef(obj=obj, field=field_tok.value, loc=_loc(ident_tok))
    if isinstance(obj, VarRef):
        return obj
    return IndexRef(array=obj.array, index=obj.index, loc=obj.loc)


# -------------------- Expressions --------------------


def parse_expression(ps: ParserState):
    return parse_or(ps)


def parse_or(ps: ParserState):
    left = parse_and(ps)
    while ps.peek().type == TokenType.OR:
        op_tok = ps.advance()
        right = parse_and(ps)
        left = BinOp(op="||", left=left, right=right, loc=_loc(op_tok))
    return left


def parse_and(ps: ParserState):
    left = parse_equality(ps)
    while ps.peek().type == TokenType.AND:
        op_tok = ps.advance()
        right = parse_equality(ps)
        left = BinOp(op="&&", left=left, right=right, loc=_loc(op_tok))
    return left


def parse_equality(ps: ParserState):
    left = parse_comparison(ps)
    while ps.peek().type in {TokenType.EQ, TokenType.NEQ}:
        op_tok = ps.advance()
        right = parse_comparison(ps)
        left = BinOp(op="==" if op_tok.type == TokenType.EQ else "!=", left=left, right=right, loc=_loc(op_tok))
    return left


def parse_comparison(ps: ParserState):
    left = parse_term(ps)
    while ps.peek().type in {TokenType.GT, TokenType.GTE, TokenType.LT, TokenType.LTE}:
        op_tok = ps.advance()
        op = ">" if op_tok.type == TokenType.GT else ">=" if op_tok.type == TokenType.GTE else "<" if op_tok.type == TokenType.LT else "<="
        right = parse_term(ps)
        left = BinOp(op=op, left=left, right=right, loc=_loc(op_tok))
    return left


def parse_term(ps: ParserState):
    left = parse_factor(ps)
    while ps.peek().type in {TokenType.PLUS, TokenType.MINUS}:
        op_tok = ps.advance()
        right = parse_factor(ps)
        left = BinOp(op="+" if op_tok.type == TokenType.PLUS else "-", left=left, right=right, loc=_loc(op_tok))
    return left


def parse_factor(ps: ParserState):
    left = parse_unary(ps)
    while ps.peek().type in {TokenType.STAR, TokenType.SLASH, TokenType.PERCENT}:
        op_tok = ps.advance()
        right = parse_unary(ps)
        if op_tok.type == TokenType.STAR:
            op = "*"
        elif op_tok.type == TokenType.SLASH:
            op = "/"
        else:
            op = "%"
        left = BinOp(op=op, left=left, right=right, loc=_loc(op_tok))
    return left


def parse_unary(ps: ParserState):
    tok = ps.peek()
    if tok.type in {TokenType.INC, TokenType.DEC}:
        ps.advance()
        inner = parse_unary(ps)
        lv = expr_to_lvalue(inner, tok)
        return IncDecExpr(op=tok.value, target=lv, is_postfix=False, loc=_loc(tok))
    if tok.type in {TokenType.NOT, TokenType.MINUS}:
        ps.advance()
        right = parse_unary(ps)
        return UnaryOp(op="!" if tok.type == TokenType.NOT else "-", right=right, loc=_loc(tok))
    return parse_postfix(ps)


def parse_postfix(ps: ParserState):
    base = parse_primary(ps)
    while ps.peek().type == TokenType.DOT:
        ps.advance()
        field_tok = ps.expect(TokenType.IDENT, "Ожидалось поле.")
        base = DotExpr(obj=base, field=field_tok.value, loc=_loc(field_tok))
    while ps.peek().type in {TokenType.INC, TokenType.DEC}:
        op_tok = ps.advance()
        lv = expr_to_lvalue(base, op_tok)
        base = IncDecExpr(op=op_tok.value, target=lv, is_postfix=True, loc=_loc(op_tok))
    return base


def parse_primary(ps: ParserState):
    tok = ps.peek()

    if ps.match(TokenType.LPAREN) is not None:
        expr = parse_expression(ps)
        ps.expect(TokenType.RPAREN, "Ожидался ')' .")
        return expr

    if tok.type == TokenType.INT:
        ps.advance()
        return Literal(value=int(tok.value), value_type=Type.from_name("бүтүн"), loc=_loc(tok))
    if tok.type == TokenType.FLOAT:
        ps.advance()
        return Literal(value=float(tok.value), value_type=Type.from_name("чыныгы"), loc=_loc(tok))
    if tok.type == TokenType.STRING:
        ps.advance()
        return Literal(value=tok.value, value_type=Type.from_name("сап"), loc=_loc(tok))
    if tok.type == TokenType.CHAR:
        ps.advance()
        return Literal(value=tok.value, value_type=Type.from_name("белги"), loc=_loc(tok))
    if tok.type == TokenType.TRUE:
        ps.advance()
        return Literal(value=True, value_type=Type.from_name("логикалык"), loc=_loc(tok))
    if tok.type == TokenType.FALSE:
        ps.advance()
        return Literal(value=False, value_type=Type.from_name("логикалык"), loc=_loc(tok))

    # input call: окуу()
    if tok.type == TokenType.INPUT:
        ps.advance()
        ps.expect(TokenType.LPAREN, "Ожидался '(' после окуу.")
        ps.expect(TokenType.RPAREN, "Ожидались ')' в окуу().")
        return InputExpr(loc=_loc(tok))

    # length builtin: узундук(expr)
    if tok.type == TokenType.LENGTH:
        ps.advance()
        ps.expect(TokenType.LPAREN, "Ожидался '(' после узундук.")
        target = parse_expression(ps)
        ps.expect(TokenType.RPAREN, "Ожидался ')' после узундук(...).")
        return CallExpr(name="узундук", args=[target], loc=_loc(tok))

    # array literal
    if ps.match(TokenType.LBRACKET) is not None:
        items: list = []
        if ps.peek().type != TokenType.RBRACKET:
            while True:
                items.append(parse_expression(ps))
                if ps.match(TokenType.COMMA) is not None:
                    continue
                break
        ps.expect(TokenType.RBRACKET, "Ожидался ']' после списка.")
        return ArrayLiteral(item_type=Type.unknown(), items=items, loc=_loc(tok))

    # identifier / call / indexing
    if tok.type == TokenType.IDENT:
        ps.advance()
        name = tok.value

        # call
        if ps.peek().type == TokenType.LPAREN:
            ps.advance()
            args: list = []
            if ps.peek().type != TokenType.RPAREN:
                while True:
                    args.append(parse_expression(ps))
                    if ps.match(TokenType.COMMA) is not None:
                        continue
                    break
            ps.expect(TokenType.RPAREN, "Ожидался ')' после аргументов.")
            expr: Expr = CallExpr(name=name, args=args, loc=_loc(tok))
        else:
            expr = VarRef(name=name, loc=_loc(tok))

        # optional indexing
        if ps.peek().type == TokenType.LBRACKET:
            lbr = ps.advance()
            idx_expr = parse_expression(ps)
            ps.expect(TokenType.RBRACKET, "Ожидался ']' в индексном выражении.")
            return IndexExpr(array=expr, index=idx_expr, loc=_loc(lbr))

        return expr

    if tok.type in {TokenType.PRINT}:
        # allow parsing `чыгар(x)` as expression; semantic will validate usage
        ps.advance()
        ps.expect(TokenType.LPAREN, "Ожидался '(' после чыгар.")
        args: list = []
        if ps.peek().type != TokenType.RPAREN:
            args.append(parse_expression(ps))
        ps.expect(TokenType.RPAREN, "Ожидался ')' после чыгар(...).")
        return CallExpr(name="чыгар", args=args, loc=_loc(tok))

    raise TILCompileError("Ожидалось выражение.", tok.line, tok.column)

