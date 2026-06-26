# aether/parser.py
from typing import List, Optional, Dict
from .tokens import Token, TokenType
from .ast_nodes import *
from .diagnostics import DiagnosticEngine, Severity, ErrorCodes
from .errors import AetherError, Diagnostic

class Parser:
    def __init__(self, tokens: List[Token], engine: DiagnosticEngine):
        self.tokens = tokens
        self.current = 0
        self.engine = engine

    def parse(self) -> Program:
        stmts = []
        while not self._is_at_end():
            try:
                stmts.append(self._declaration())
            except AetherError as e:
                self.engine.diagnostics.append(e.diag)
                self._synchronize()
        return Program(1, 1, stmts)

    def _synchronize(self):
        while not self._is_at_end():
            if self._previous().type == TokenType.SEMICOLON: return
            if self._peek().type in [TokenType.NAMESPACE, TokenType.FN, TokenType.LET, TokenType.IF, TokenType.FOR, TokenType.RETURN, TokenType.RAW_CMD]: return
            self._advance()

    def _peek(self, offset=0): 
        i = self.current + offset
        return self.tokens[i] if i < len(self.tokens) else self.tokens[-1]
    def _previous(self): return self.tokens[self.current - 1]
    def _is_at_end(self): return self._peek().type == TokenType.EOF
    def _advance(self):
        if not self._is_at_end(): self.current += 1
        return self._previous()
    def _check(self, *types): return not self._is_at_end() and self._peek().type in types
    def _match(self, *types):
        for t in types:
            if self._check(t): self._advance(); return True
        return False
    def _expect(self, t: TokenType, msg: str) -> Token:
        if self._check(t): return self._advance()
        tok = self._peek()
        raise AetherError(Diagnostic(ErrorCodes.EXPECTED_TOKEN, Severity.ERROR, f"{msg} (Got {tok.type.name})", tok.line, tok.col, self.engine.filename, self.engine.source))

    def _declaration(self):
        if self._match(TokenType.NAMESPACE):
            tok = self._previous()
            name = self._expect(TokenType.IDENT, "Expected namespace name").value
            return NamespaceDecl(tok.line, tok.col, name)
        if self._match(TokenType.FN):
            return self._function_decl()
        return self._statement()

    def _function_decl(self) -> FunctionDecl:
        tok = self._previous()
        name = self._expect(TokenType.IDENT, "Expected function name").value
        self._expect(TokenType.LPAREN, "Expected '('")
        params = []
        if not self._check(TokenType.RPAREN):
            while True:
                p_name = self._expect(TokenType.IDENT, "Expected param name").value
                self._expect(TokenType.COLON, "Expected ':'")
                p_type = self._type_node()
                params.append(Param(tok.line, tok.col, p_name, p_type))
                if not self._match(TokenType.COMMA): break
        self._expect(TokenType.RPAREN, "Expected ')'")
        ret_type = self._type_node() if self._match(TokenType.ARROW) else None
        body = self._block()
        return FunctionDecl(tok.line, tok.col, name, params, ret_type, body)

    def _block(self) -> Block:
        lb = self._expect(TokenType.LBRACE, "Expected '{'")
        stmts = []
        while not self._check(TokenType.RBRACE) and not self._is_at_end():
            stmts.append(self._statement())
        self._expect(TokenType.RBRACE, "Expected '}'")
        return Block(lb.line, lb.col, stmts)

    def _statement(self):
        if self._match(TokenType.LET): return self._var_decl()
        if self._match(TokenType.IF): return self._if_stmt()
        if self._match(TokenType.FOR): return self._for_stmt()
        if self._match(TokenType.RETURN): return self._return_stmt()
        if self._match(TokenType.RAW_CMD):
            tok = self._previous()
            return RawCommandStmt(tok.line, tok.col, tok.value)
        return self._expr_stmt()

    def _var_decl(self) -> VariableDecl:
        tok = self._previous()
        is_mut = self._match(TokenType.MUT)
        name = self._expect(TokenType.IDENT, "Expected variable name").value
        var_type = self._type_node() if self._match(TokenType.COLON) else None
        self._expect(TokenType.ASSIGN, "Expected '='")
        val = self._expression()
        self._match(TokenType.SEMICOLON)
        return VariableDecl(tok.line, tok.col, name, var_type, val, is_mut)

    def _if_stmt(self):
        tok = self._previous()
        cond = self._expression()
        then_block = self._block()
        else_stmt = None
        if self._match(TokenType.ELSE):
            else_stmt = self._block()
        return IfStmt(tok.line, tok.col, cond, then_block, else_stmt)

    def _for_stmt(self):
        tok = self._previous()
        var = self._expect(TokenType.IDENT, "Expected loop var").value
        self._expect(TokenType.IN, "Expected 'in'")
        start = self._expression()
        self._expect(TokenType.DOTDOT, "Expected '..'")
        end = self._expression()
        body = self._block()
        return ForStmt(tok.line, tok.col, var, start, end, body)

    def _return_stmt(self):
        tok = self._previous()
        val = None
        if not self._check(TokenType.SEMICOLON) and not self._check(TokenType.RBRACE):
            val = self._expression()
        self._match(TokenType.SEMICOLON)
        return ReturnStmt(tok.line, tok.col, val)

    def _expr_stmt(self):
        tok = self._peek()
        expr = self._expression()
        if self._match(TokenType.ASSIGN, TokenType.PLUSEQ, TokenType.MINUSEQ, TokenType.STAREQ, TokenType.SLASHEQ, TokenType.PERCENTEQ):
            op_tok = self._previous()
            val = self._expression()
            self._match(TokenType.SEMICOLON)
            if op_tok.type == TokenType.ASSIGN: return Assignment(tok.line, tok.col, expr, val)
            return CompoundAssign(tok.line, tok.col, expr, op_tok.value, val)
        self._match(TokenType.SEMICOLON)
        return ExprStmt(tok.line, tok.col, expr)

    def _type_node(self):
        tok = self._peek()
        if tok.type in [TokenType.INT_TYPE, TokenType.STRING_TYPE, TokenType.BOOL_TYPE, TokenType.IDENT]:
            self._advance()
            name = tok.value
            if self._match(TokenType.LBRACKET):
                self._expect(TokenType.RBRACKET, "Expected ']'")
                name += "[]"
            return TypeNode(tok.line, tok.col, name)
        return None

    def _expression(self): return self._logical_or()
    def _logical_or(self):
        e = self._logical_and()
        while self._match(TokenType.OR): e = BinaryOp(e.line, e.col, e, "||", self._logical_and())
        return e
    def _logical_and(self):
        e = self._equality()
        while self._match(TokenType.AND): e = BinaryOp(e.line, e.col, e, "&&", self._equality())
        return e
    def _equality(self):
        e = self._comparison()
        while self._match(TokenType.EQ, TokenType.NEQ): e = BinaryOp(e.line, e.col, e, self._previous().value, self._comparison())
        return e
    def _comparison(self):
        e = self._term()
        while self._match(TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE): e = BinaryOp(e.line, e.col, e, self._previous().value, self._term())
        return e
    def _term(self):
        e = self._factor()
        while self._match(TokenType.PLUS, TokenType.MINUS): e = BinaryOp(e.line, e.col, e, self._previous().value, self._factor())
        return e
    def _factor(self):
        e = self._unary()
        while self._match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT): e = BinaryOp(e.line, e.col, e, self._previous().value, self._unary())
        return e
    def _unary(self):
        if self._match(TokenType.NOT): return UnaryOp(self._previous().line, self._previous().col, "!", self._unary())
        if self._match(TokenType.MINUS): return UnaryOp(self._previous().line, self._previous().col, "-", self._unary())
        return self._primary()

    def _primary(self):
        tok = self._peek()
        if self._match(TokenType.TRUE): return Literal(tok.line, tok.col, True, "bool")
        if self._match(TokenType.FALSE): return Literal(tok.line, tok.col, False, "bool")
        if self._match(TokenType.INT): return Literal(tok.line, tok.col, int(tok.value), "int")
        if self._match(TokenType.STRING): return Literal(tok.line, tok.col, tok.value, "string")
        if self._match(TokenType.LPAREN):
            e = self._expression()
            self._expect(TokenType.RPAREN, "Expected ')'")
            return e
        if self._match(TokenType.LBRACKET):
            elements = []
            if not self._check(TokenType.RBRACKET):
                while True:
                    elements.append(self._expression())
                    if not self._match(TokenType.COMMA): break
            self._expect(TokenType.RBRACKET, "Expected ']'")
            return ArrayLiteral(tok.line, tok.col, elements)
            
        if self._match(TokenType.IDENT):
            ident_tok = self._previous()
            if self._match(TokenType.LPAREN):
                args = []
                if not self._check(TokenType.RPAREN):
                    while True:
                        args.append(self._expression())
                        if not self._match(TokenType.COMMA): break
                self._expect(TokenType.RPAREN, "Expected ')'")
                return FunctionCall(ident_tok.line, ident_tok.col, ident_tok.value, args)
            expr = Identifier(ident_tok.line, ident_tok.col, ident_tok.value)
            return self._postfix(expr)
        raise AetherError(Diagnostic(ErrorCodes.UNEXPECTED_TOKEN, Severity.ERROR, f"Unexpected token {tok.type.name}", tok.line, tok.col, self.engine.filename, self.engine.source))

    def _postfix(self, expr):
        while True:
            if self._match(TokenType.LBRACKET):
                idx = self._expression()
                self._expect(TokenType.RBRACKET, "Expected ']'")
                expr = IndexAccess(expr.line, expr.col, expr, idx)
            else: break
        return expr