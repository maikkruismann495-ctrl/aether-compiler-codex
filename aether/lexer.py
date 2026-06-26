# aether/lexer.py
from typing import List
from .tokens import Token, TokenType, KEYWORDS
from .errors import AetherError, Diagnostic
from .diagnostics import DiagnosticEngine, Severity, ErrorCodes

class Lexer:
    def __init__(self, source: str, engine: DiagnosticEngine):
        self.source = source
        self.engine = engine
        self.tokens: List[Token] = []
        self.pos = 0
        self.line = 1
        self.col = 1

    def tokenize(self) -> List[Token]:
        while not self._is_at_end():
            char = self._peek()
            if char in ' \t\r\n':
                if char == '\n': self.line += 1; self.col = 1
                else: self.col += 1
                self.pos += 1
                continue
            if char == '/' and self._peek(1) == '/':
                while not self._is_at_end() and self._peek() != '\n':
                    self.pos += 1; self.col += 1
                continue
            if char == '/' and not self._peek(1).isspace():
                self._read_raw_command()
                continue
            if char.isdigit(): self._read_number()
            elif char.isalpha() or char == '_': self._read_identifier()
            elif char == '"': self._read_string()
            else: self._read_operator()
        self.tokens.append(Token(TokenType.EOF, "", self.line, self.col))
        return self.tokens

    def _peek(self, offset=0):
        if self.pos + offset >= len(self.source): return '\0'
        return self.source[self.pos + offset]

    def _advance(self):
        char = self.source[self.pos]
        self.pos += 1; self.col += 1
        return char

    def _is_at_end(self):
        return self.pos >= len(self.source)

    def _read_raw_command(self):
        start_line, start_col = self.line, self.col
        cmd_str = self._advance() # Consume '/'
        while not self._is_at_end() and self._peek() != '\n':
            cmd_str += self._advance()
        self.tokens.append(Token(TokenType.RAW_CMD, cmd_str, start_line, start_col))

    def _read_number(self):
        start_col = self.col
        num = ""
        while not self._is_at_end() and self._peek().isdigit():
            num += self._advance()
        self.tokens.append(Token(TokenType.INT, num, self.line, start_col))

    def _read_identifier(self):
        start_col = self.col
        ident = ""
        while not self._is_at_end() and (self._peek().isalnum() or self._peek() == '_'):
            ident += self._advance()
        self.tokens.append(Token(KEYWORDS.get(ident, TokenType.IDENT), ident, self.line, start_col))

    def _read_string(self):
        start_col = self.col
        self._advance() # Consume '"'
        s = ""
        while not self._is_at_end() and self._peek() != '"':
            if self._peek() == '\\':
                self._advance()
                nxt = self._advance()
                if nxt == 'n': s += '\n'
                elif nxt == 't': s += '\t'
                else: s += nxt
            else:
                s += self._advance()
        if self._is_at_end():
            self.engine.report(ErrorCodes.UNTERMINATED_STRING, Severity.ERROR, "Unterminated string", self.line, start_col)
            raise AetherError(Diagnostic(ErrorCodes.UNTERMINATED_STRING, Severity.ERROR, "Unterminated string", self.line, start_col, self.engine.filename, self.engine.source))
        self._advance() # Consume closing '"'
        self.tokens.append(Token(TokenType.STRING, s, self.line, start_col))

    def _read_operator(self):
        start_col = self.col
        char = self._advance()
        two_char = char + self._peek()
        if two_char in ["==", "!=", "<=", ">=", "+=", "-=", "*=", "/=", "%=", "->", ".."]:
            self._advance()
            tt_map = {"==": TokenType.EQ, "!=": TokenType.NEQ, "<=": TokenType.LTE, ">=": TokenType.GTE,
                      "+=": TokenType.PLUSEQ, "-=": TokenType.MINUSEQ, "*=": TokenType.STAREQ, "/=": TokenType.SLASHEQ,
                      "%=": TokenType.PERCENTEQ, "->": TokenType.ARROW, "..": TokenType.DOTDOT}
            self.tokens.append(Token(tt_map[two_char], two_char, self.line, start_col))
            return
        single_map = {
            "+": TokenType.PLUS, "-": TokenType.MINUS, "*": TokenType.STAR, "/": TokenType.SLASH, "%": TokenType.PERCENT,
            "=": TokenType.ASSIGN, "<": TokenType.LT, ">": TokenType.GT,
            "(": TokenType.LPAREN, ")": TokenType.RPAREN, "{": TokenType.LBRACE, "}": TokenType.RBRACE,
            "[": TokenType.LBRACKET, "]": TokenType.RBRACKET, ":": TokenType.COLON, ";": TokenType.SEMICOLON,
            ",": TokenType.COMMA, ".": TokenType.DOT
        }
        if char in single_map:
            self.tokens.append(Token(single_map[char], char, self.line, start_col))
        else:
            self.engine.report(ErrorCodes.UNEXPECTED_CHAR, Severity.ERROR, f"Unexpected character: '{char}'", self.line, start_col)
            raise AetherError(Diagnostic(ErrorCodes.UNEXPECTED_CHAR, Severity.ERROR, f"Unexpected character: '{char}'", self.line, start_col, self.engine.filename, self.engine.source))