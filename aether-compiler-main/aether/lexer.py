# aether/lexer.py
from typing import List
from .tokens import Token, TokenType, KEYWORDS
from .errors import AetherError, Diagnostic
from .diagnostics import DiagnosticEngine, Severity, ErrorCodes

RAW_CONDITION_STARTERS = {"score", "entity", "block", "blocks", "data", "predicate", "dimension", "biome", "loaded", "items"}

LANGUAGE_LINE_STARTERS = {"namespace", "function", "fn", "let", "const", "var", "if", "else", "for", "return"}
CODE_AFTER_IDENTIFIER = set("=+-*/%([.;,<>!")

class Lexer:
    def __init__(self, source: str, engine: DiagnosticEngine):
        self.source = source
        self.engine = engine
        self.tokens: List[Token] = []
        self.pos = 0
        self.line = 1
        self.col = 1
        self.block_depth = 0

    def tokenize(self) -> List[Token]:
        while not self._is_at_end():
            char = self._peek()
            if char in ' \t\r\n':
                if char == '\n': self.line += 1; self.col = 1
                else: self.col += 1
                self.pos += 1
                continue
            if char == '#' and self._at_line_start():
                self._skip_line()
                continue
            if char == '/' and self._peek(1) == '/':
                self._skip_line()
                continue
            if self._try_read_structured_header():
                continue
            if char == '/' and self._at_line_start():
                self._read_raw_command()
                continue
            if self._at_line_start() and self._looks_like_bare_raw_command():
                self._read_bare_raw_command()
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

    def _skip_line(self):
        while not self._is_at_end() and self._peek() != '\n':
            self.pos += 1
            self.col += 1

    def _at_line_start(self):
        i = self.pos - 1
        while i >= 0 and self.source[i] not in '\n\r':
            if self.source[i] not in ' \t':
                return False
            i -= 1
        return True

    def _line_end(self):
        end = self.source.find('\n', self.pos)
        return len(self.source) if end == -1 else end

    def _word_at(self, pos):
        end = pos
        while end < len(self.source) and (self.source[end].isalnum() or self.source[end] in "_-"):
            end += 1
        return self.source[pos:end], end

    def _skip_inline_space(self, pos):
        while pos < len(self.source) and self.source[pos] in ' \t':
            pos += 1
        return pos

    def _find_header_brace(self, line_end):
        idx = self.source.rfind("{", self.pos, line_end)
        while idx != -1:
            if not self.source[idx + 1:line_end].strip():
                return idx
            idx = self.source.rfind("{", self.pos, idx)
        return None

    def _emit_header(self, token_type: TokenType, word: str, word_end: int, brace_pos: int):
        start_pos, start_line, start_col = self.pos, self.line, self.col
        self.tokens.append(Token(token_type, word, start_line, start_col))

        raw_start = self._skip_inline_space(word_end)
        raw_value = self.source[raw_start:brace_pos].strip()
        if raw_value:
            raw_col = start_col + (raw_start - start_pos)
            self.tokens.append(Token(TokenType.RAW_TEXT, raw_value, start_line, raw_col))

        self.pos = brace_pos
        self.col = start_col + (brace_pos - start_pos)
        self.tokens.append(Token(TokenType.LBRACE, "{", self.line, self.col))
        self.block_depth += 1
        self.pos += 1
        self.col += 1

    def _try_read_structured_header(self):
        if not self._at_line_start() or not (self._peek().isalpha() or self._peek() == "_"):
            return False

        word, word_end = self._word_at(self.pos)
        line_end = self._line_end()
        brace_pos = self._find_header_brace(line_end)
        if brace_pos is None:
            return False

        if word == "execute":
            self._emit_header(TokenType.EXECUTE, word, word_end, brace_pos)
            return True

        if word == "if":
            cond_start = self._skip_inline_space(word_end)
            cond_word, _ = self._word_at(cond_start)
            if cond_word in RAW_CONDITION_STARTERS:
                self._emit_header(TokenType.IF, word, word_end, brace_pos)
                return True

        return False

    def _looks_like_function_decl(self, word_end):
        pos = self._skip_inline_space(word_end)
        name, pos = self._word_at(pos)
        if not name:
            return False
        pos = self._skip_inline_space(pos)
        return pos < len(self.source) and self.source[pos] == "("

    def _looks_like_bare_raw_command(self):
        word, word_end = self._word_at(self.pos)
        if not word or self.block_depth <= 0:
            return False

        if word == "function":
            return not self._looks_like_function_decl(word_end)

        line_end = self._line_end()
        rest_start = self._skip_inline_space(word_end)
        rest = self.source[rest_start:line_end].strip()

        if word == "return":
            return rest.startswith("run ") or rest == "fail"

        if word in LANGUAGE_LINE_STARTERS:
            return False

        if rest_start >= line_end:
            return True

        if self.source[rest_start] in CODE_AFTER_IDENTIFIER:
            return False

        return True

    def _read_raw_command(self):
        start_line, start_col = self.line, self.col
        cmd_str = self._advance() # Consume '/'
        while not self._is_at_end() and self._peek() != '\n':
            cmd_str += self._advance()
        self.tokens.append(Token(TokenType.RAW_CMD, cmd_str, start_line, start_col))

    def _read_bare_raw_command(self):
        start_line, start_col = self.line, self.col
        cmd_str = "/"
        while not self._is_at_end() and self._peek() != '\n':
            cmd_str += self._advance()
        self.tokens.append(Token(TokenType.RAW_CMD, cmd_str.strip(), start_line, start_col))

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
        if two_char in ["==", "!=", "<=", ">=", "+=", "-=", "*=", "/=", "%=", "->", "..", "&&", "||", "++", "--"]:
            self._advance()
            tt_map = {"==": TokenType.EQ, "!=": TokenType.NEQ, "<=": TokenType.LTE, ">=": TokenType.GTE,
                      "+=": TokenType.PLUSEQ, "-=": TokenType.MINUSEQ, "*=": TokenType.STAREQ, "/=": TokenType.SLASHEQ,
                      "%=": TokenType.PERCENTEQ, "->": TokenType.ARROW, "..": TokenType.DOTDOT,
                      "&&": TokenType.AND, "||": TokenType.OR, "++": TokenType.PLUSPLUS, "--": TokenType.MINUSMINUS}
            self.tokens.append(Token(tt_map[two_char], two_char, self.line, start_col))
            return
        single_map = {
            "+": TokenType.PLUS, "-": TokenType.MINUS, "*": TokenType.STAR, "/": TokenType.SLASH, "%": TokenType.PERCENT,
            "!": TokenType.NOT,
            "=": TokenType.ASSIGN, "<": TokenType.LT, ">": TokenType.GT,
            "(": TokenType.LPAREN, ")": TokenType.RPAREN, "{": TokenType.LBRACE, "}": TokenType.RBRACE,
            "[": TokenType.LBRACKET, "]": TokenType.RBRACKET, ":": TokenType.COLON, ";": TokenType.SEMICOLON,
            ",": TokenType.COMMA, ".": TokenType.DOT
        }
        if char in single_map:
            self.tokens.append(Token(single_map[char], char, self.line, start_col))
            if char == "{":
                self.block_depth += 1
            elif char == "}":
                self.block_depth = max(0, self.block_depth - 1)
        else:
            self.engine.report(ErrorCodes.UNEXPECTED_CHAR, Severity.ERROR, f"Unexpected character: '{char}'", self.line, start_col)
            raise AetherError(Diagnostic(ErrorCodes.UNEXPECTED_CHAR, Severity.ERROR, f"Unexpected character: '{char}'", self.line, start_col, self.engine.filename, self.engine.source))
