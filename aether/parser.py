# src/aether/parser.py

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
        self.struct_names = set()

    def parse(self) -> Program:
        stmts = []
        while not self._is_at_end():
            try:
                stmts.append(self._declaration())
                self._consume_newlines()
            except AetherError as e:
                self.engine.diagnostics.append(e.diag)
                self._synchronize()
        return Program(1, 1, stmts)

    def _synchronize(self):
        while not self._is_at_end():
            if self._previous().type == TokenType.NEWLINE:
                return
            if self._peek().type in [TokenType.NAMESPACE, TokenType.CLASS, TokenType.DEF, TokenType.IF, TokenType.FOR, TokenType.WHILE, TokenType.LOCAL, TokenType.EXECUTE]:
                return
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
        hint = None
        if t == TokenType.COLON: hint = "Did you forget a ':' at the end of the statement?"
        raise AetherError(Diagnostic(ErrorCodes.EXPECTED_TOKEN, Severity.ERROR, f"{msg} (Got {tok.type.name})", tok.line, tok.col, self.engine.filename, self.engine.source, hint))
    def _consume_newlines(self):
        while self._match(TokenType.NEWLINE): pass

    def _declaration(self):
        self._consume_newlines()
        if self._match(TokenType.NAMESPACE): return self._namespace_decl()
        if self._match(TokenType.CLASS): return self._class_decl()
        if self._match(TokenType.DEF): return self._function_decl()
        return self._statement()

    def _namespace_decl(self):
        tok = self._previous()
        name = self._expect(TokenType.IDENT, "Expected namespace name").value
        return NamespaceDecl(tok.line, tok.col, name)

    def _class_decl(self):
        tok = self._previous()
        name = self._expect(TokenType.IDENT, "Expected class name").value
        self._expect(TokenType.COLON, "Expected ':' after class name")
        self._expect(TokenType.NEWLINE, "Expected newline")
        self._expect(TokenType.INDENT, "Expected indented block")
        fields: Dict[str, str] = {}
        methods: List[FunctionDecl] = []
        while not self._check(TokenType.DEDENT) and not self._is_at_end():
            self._consume_newlines()
            if self._match(TokenType.DEF):
                methods.append(self._function_decl(is_method=True))
            elif self._check(TokenType.IDENT):
                fname = self._advance().value
                self._expect(TokenType.COLON, "Expected ':' after field name")
                ftype = self._type_node().name
                fields[fname] = ftype
                self._match(TokenType.NEWLINE)
            self._consume_newlines()
        self._expect(TokenType.DEDENT, "Expected dedent to close class")
        return ClassDecl(tok.line, tok.col, name, fields, methods)

    def _function_decl(self, is_method=False) -> FunctionDecl:
        tok = self._previous()
        name = self._expect(TokenType.IDENT, "Expected function name").value
        self._expect(TokenType.LPAREN, "Expected '('")
        params = []
        if not self._check(TokenType.RPAREN):
            while True:
                if self._check(TokenType.SELF): p_name = self._advance().value
                else: p_name = self._expect(TokenType.IDENT, "Expected param name").value
                self._expect(TokenType.COLON, "Expected ':'")
                p_type = self._type_node()
                params.append(Param(tok.line, tok.col, p_name, p_type))
                if not self._match(TokenType.COMMA): break
        self._expect(TokenType.RPAREN, "Expected ')'")
        ret_type = self._type_node() if self._match(TokenType.ARROW) else None
        self._expect(TokenType.COLON, "Expected ':'")
        self._expect(TokenType.NEWLINE, "Expected newline")
        body = self._block()
        return FunctionDecl(tok.line, tok.col, name, params, ret_type, body, is_method)

    def _block(self) -> Block:
        self._consume_newlines()
        self._expect(TokenType.INDENT, "Expected indented block")
        stmts = []
        while not self._check(TokenType.DEDENT) and not self._is_at_end():
            stmts.append(self._statement())
            self._consume_newlines()
        self._expect(TokenType.DEDENT, "Expected dedent")
        return Block(self._peek().line, self._peek().col, stmts)

    def _statement(self):
        decorator = None
        if self._match(TokenType.AT):
            dec_tok = self._previous()
            dec_name = self._expect(TokenType.IDENT, "Expected decorator name").value
            if dec_name != "objective":
                raise AetherError(Diagnostic(ErrorCodes.UNEXPECTED_TOKEN, Severity.ERROR, f"Unknown decorator '@{dec_name}'", dec_tok.line, dec_tok.col, self.engine.filename, self.engine.source))
            self._expect(TokenType.LPAREN, "Expected '(' after @objective")
            obj_tok = self._expect(TokenType.STRING, "Expected objective name string")
            self._expect(TokenType.RPAREN, "Expected ')'")
            decorator = obj_tok.value
        if self._match(TokenType.LOCAL): return self._var_decl(decorator)
        if self._match(TokenType.IF): return self._if_stmt()
        if self._match(TokenType.FOR): return self._for_stmt()
        if self._match(TokenType.WHILE): return self._while_stmt()
        if self._match(TokenType.EXECUTE): return self._execute_stmt()
        if self._match(TokenType.RETURN): return self._return_stmt()
        return self._expr_stmt()

    def _execute_stmt(self):
        tok = self._previous()
        chain = []
        while not self._check(TokenType.COLON):
            sub_cmd = self._expect(TokenType.IDENT, "Expected execute sub-command (as, at, if, etc.)").value
            sel = self._expression()
            chain.append((sub_cmd, sel))
        self._expect(TokenType.COLON, "Expected ':' after execute chain")
        self._expect(TokenType.NEWLINE, "Expected newline")
        body = self._block()
        return ExecuteStmt(tok.line, tok.col, chain, body)

    def _var_decl(self, decorator=None) -> VariableDecl:
        tok = self._previous()
        name = self._expect(TokenType.IDENT, "Expected variable name").value
        var_type = self._type_node() if self._match(TokenType.COLON) else None
        self._expect(TokenType.ASSIGN, "Expected '=' after variable declaration.")
        val = self._expression()
        return VariableDecl(tok.line, tok.col, name, var_type, val, decorator)

    def _if_stmt(self):
        tok = self._previous()
        cond = self._expression()
        self._expect(TokenType.COLON, "Expected ':'")
        self._expect(TokenType.NEWLINE, "Expected newline")
        then_block = self._block()
        elifs = []
        else_stmt = None
        while self._match(TokenType.ELIF):
            e_tok = self._previous()
            e_cond = self._expression()
            self._expect(TokenType.COLON, "Expected ':'")
            self._expect(TokenType.NEWLINE, "Expected newline")
            e_block = self._block()
            elifs.append(IfStmt(e_tok.line, e_tok.col, e_cond, e_block, [], None))
        if self._match(TokenType.ELSE):
            self._expect(TokenType.COLON, "Expected ':'")
            self._expect(TokenType.NEWLINE, "Expected newline")
            else_stmt = self._block()
        return IfStmt(tok.line, tok.col, cond, then_block, elifs, else_stmt)

    def _for_stmt(self):
        tok = self._previous()
        var = self._expect(TokenType.IDENT, "Expected loop var").value
        self._expect(TokenType.IN, "Expected 'in'")
        start = self._expression()
        self._expect(TokenType.RANGE, "Expected 'range'")
        self._expect(TokenType.LPAREN, "Expected '('")
        end = self._expression()
        self._expect(TokenType.RPAREN, "Expected ')'")
        self._expect(TokenType.COLON, "Expected ':'")
        self._expect(TokenType.NEWLINE, "Expected newline")
        body = self._block()
        return ForStmt(tok.line, tok.col, var, start, end, body)

    def _while_stmt(self):
        tok = self._previous()
        cond = self._expression()
        self._expect(TokenType.COLON, "Expected ':'")
        self._expect(TokenType.NEWLINE, "Expected newline")
        body = self._block()
        return WhileStmt(tok.line, tok.col, cond, body)

    def _return_stmt(self):
        tok = self._previous()
        val = None if self._check(TokenType.NEWLINE) else self._expression()
        return ReturnStmt(tok.line, tok.col, val)

    def _expr_stmt(self):
        tok = self._peek()
        expr = self._expression()
        if self._match(TokenType.ASSIGN, TokenType.PLUSEQ, TokenType.MINUSEQ, TokenType.STAREQ, TokenType.SLASHEQ, TokenType.PERCENTEQ):
            op_tok = self._previous()
            val = self._expression()
            if op_tok.type == TokenType.ASSIGN: return Assignment(tok.line, tok.col, expr, val)
            return CompoundAssign(tok.line, tok.col, expr, op_tok.value, val)
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
        raise AetherError(Diagnostic(ErrorCodes.EXPECTED_TOKEN, Severity.ERROR, f"Expected type, got {tok.type.name}", tok.line, tok.col, self.engine.filename, self.engine.source))

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
        if self._match(TokenType.FORMAT_STRING): return self._parse_format_string(tok)
        if self._match(TokenType.SELF): return Identifier(tok.line, tok.col, "self")
        if self._match(TokenType.LPAREN):
            expr = self._expression()
            if self._match(TokenType.COMMA):
                elements = [expr]
                while not self._check(TokenType.RPAREN):
                    elements.append(self._expression())
                    if not self._match(TokenType.COMMA): break
                self._expect(TokenType.RPAREN, "Expected ')'")
                return TupleLiteral(tok.line, tok.col, elements)
            self._expect(TokenType.RPAREN, "Expected ')'")
            return expr
        if self._match(TokenType.LBRACKET):
            elements = []
            if not self._check(TokenType.RBRACKET):
                while True:
                    elements.append(self._expression())
                    if not self._match(TokenType.COMMA): break
            self._expect(TokenType.RBRACKET, "Expected ']'")
            return Literal(tok.line, tok.col, elements, "array")
        if self._match(TokenType.LBRACE):
            elements = {}
            if not self._check(TokenType.RBRACE):
                while True:
                    key = self._expect(TokenType.STRING, "Expected string key in dict").value
                    self._expect(TokenType.COLON, "Expected ':' after dict key")
                    val = self._expression()
                    elements[key] = val
                    if not self._match(TokenType.COMMA): break
            self._expect(TokenType.RBRACE, "Expected '}'")
            return DictLiteral(tok.line, tok.col, elements)
            
        if self._match(TokenType.IDENT):
            ident_tok = self._previous()
            if self._match(TokenType.LPAREN):
                args, kwargs = self._parse_args()
                self._expect(TokenType.RPAREN, "Expected ')'")
                return FunctionCall(ident_tok.line, ident_tok.col, None, ident_tok.value, args, kwargs)
            expr = Identifier(ident_tok.line, ident_tok.col, ident_tok.value)
            return self._postfix(expr)
        raise AetherError(Diagnostic(ErrorCodes.UNEXPECTED_TOKEN, Severity.ERROR, f"Unexpected token {tok.type.name}", tok.line, tok.col, self.engine.filename, self.engine.source))

    def _parse_format_string(self, tok: Token) -> FormatString:
        raw = tok.value
        parts = []
        last = 0
        i = 0
        while i < len(raw):
            if raw[i] == '{':
                if i > last: parts.append(raw[last:i])
                j = raw.find('}', i)
                if j == -1: raise AetherError(Diagnostic(ErrorCodes.UNTERMINATED_STRING, Severity.ERROR, "Unterminated format string", tok.line, tok.col, self.engine.filename, self.engine.source))
                var_name = raw[i+1:j]
                parts.append(Identifier(tok.line, tok.col + i, var_name))
                last = j + 1
                i = j + 1
            else:
                i += 1
        if last < len(raw): parts.append(raw[last:])
        return FormatString(tok.line, tok.col, parts)

    def _parse_args(self):
        args, kwargs = [], {}
        if not self._check(TokenType.RPAREN):
            while True:
                if self._check(TokenType.IDENT) and self._peek(1).type == TokenType.ASSIGN:
                    k_tok = self._advance()
                    self._advance() # consume '='
                    kwargs[k_tok.value] = self._expression()
                else:
                    args.append(self._expression())
                if not self._match(TokenType.COMMA): break
        return args, kwargs

    def _postfix(self, expr):
        while True:
            if self._match(TokenType.DOT):
                tok = self._previous()
                m_name = self._expect(TokenType.IDENT, "Expected member name").value
                if self._match(TokenType.LPAREN):
                    args, kwargs = self._parse_args()
                    self._expect(TokenType.RPAREN, "Expected ')'")
                    return MethodCall(tok.line, tok.col, expr, m_name, args)
                expr = MemberAccess(tok.line, tok.col, expr, m_name)
            elif self._match(TokenType.LBRACKET):
                idx = self._expression()
                self._expect(TokenType.RBRACKET, "Expected ']'")
                expr = IndexAccess(expr.line, expr.col, expr, idx)
            else: break
        return expr