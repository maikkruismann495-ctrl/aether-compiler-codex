# aether/lexer.py

from typing import List
from .tokens import Token, TokenType, KEYWORDS
from .diagnostics import DiagnosticEngine, Severity, ErrorCodes
from .errors import AetherError, Diagnostic

class Lexer:
    """
    Transforms raw Aether source code into a flat list of Tokens.
    Handles Python-style indentation by generating INDENT and DEDENT tokens.
    """
    def __init__(self, source: str, engine: DiagnosticEngine):
        self.source = source
        self.engine = engine
        self.tokens: List[Token] = []
        self.indent_stack = [0]

    def tokenize(self) -> List[Token]:
        lines = self.source.split('\n')
        for line_num, line in enumerate(lines, 1):
            self._tokenize_line(line, line_num)
            
        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            self.tokens.append(Token(TokenType.DEDENT, "", len(lines), 1))
            
        self.tokens.append(Token(TokenType.EOF, "", len(lines), 1))
        return self.tokens

    def _tokenize_line(self, line: str, line_num: int):
        stripped = line.lstrip()
        if not stripped or stripped.startswith('#'):
            return
            
        indent = len(line) - len(stripped)
        if indent > self.indent_stack[-1]:
            self.indent_stack.append(indent)
            self.tokens.append(Token(TokenType.INDENT, "", line_num, 1))
        elif indent < self.indent_stack[-1]:
            while indent < self.indent_stack[-1]:
                self.indent_stack.pop()
                self.tokens.append(Token(TokenType.DEDENT, "", line_num, 1))
                
        col = indent + 1
        text = stripped
        
        while text:
            char = text[0]
            if char in ' \t':
                text = text[1:]; col += 1; continue
            
            if char.isdigit():
                num = ""
                while text and text[0].isdigit():
                    num += text[0]; text = text[1:]; col += 1
                self.tokens.append(Token(TokenType.INT, num, line_num, col - len(num)))
            elif char.isalpha() or char == '_':
                ident = ""
                while text and (text[0].isalnum() or text[0] == '_'):
                    ident += text[0]; text = text[1:]; col += 1
                self.tokens.append(Token(KEYWORDS.get(ident, TokenType.IDENT), ident, line_num, col - len(ident)))
            elif char == 'f' and len(text) > 1 and text[1] == '"':
                text = text[2:]; col += 2
                string_str = ""
                while text and text[0] != '"':
                    if text[0] == '\\':
                        nxt = text[1]
                        if nxt == 'n': string_str += '\n'
                        elif nxt == 't': string_str += '\t'
                        else: string_str += nxt
                        text = text[2:]; col += 2
                    else:
                        string_str += text[0]; text = text[1:]; col += 1
                if not text:
                    self.engine.report(ErrorCodes.UNTERMINATED_STRING, Severity.ERROR, "Unterminated format string", line_num, col)
                    raise AetherError(Diagnostic(ErrorCodes.UNTERMINATED_STRING, Severity.ERROR, "Unterminated format string", line_num, col, self.engine.filename, self.engine.source))
                text = text[1:]; col += 1
                self.tokens.append(Token(TokenType.FORMAT_STRING, string_str, line_num, col))
            elif char == '"':
                text = text[1:]; col += 1
                string_str = ""
                while text and text[0] != '"':
                    if text[0] == '\\':
                        nxt = text[1]
                        if nxt == 'n': string_str += '\n'
                        elif nxt == 't': string_str += '\t'
                        else: string_str += nxt
                        text = text[2:]; col += 2
                    else:
                        string_str += text[0]; text = text[1:]; col += 1
                if not text:
                    self.engine.report(ErrorCodes.UNTERMINATED_STRING, Severity.ERROR, "Unterminated string", line_num, col)
                    raise AetherError(Diagnostic(ErrorCodes.UNTERMINATED_STRING, Severity.ERROR, "Unterminated string", line_num, col, self.engine.filename, self.engine.source))
                text = text[1:]; col += 1
                self.tokens.append(Token(TokenType.STRING, string_str, line_num, col))
            else:
                matched = False
                for op, tt in [("==", TokenType.EQ), ("!=", TokenType.NEQ), ("<=", TokenType.LTE), (">=", TokenType.GTE),
                               ("+=", TokenType.PLUSEQ), ("-=", TokenType.MINUSEQ), ("*=", TokenType.STAREQ), ("/=", TokenType.SLASHEQ),
                               ("%=", TokenType.PERCENTEQ), ("->", TokenType.ARROW),
                               ("+", TokenType.PLUS), ("-", TokenType.MINUS), ("*", TokenType.STAR), ("/", TokenType.SLASH), ("%", TokenType.PERCENT),
                               ("=", TokenType.ASSIGN), ("<", TokenType.LT), (">", TokenType.GT),
                               ("(", TokenType.LPAREN), (")", TokenType.RPAREN), ("[", TokenType.LBRACKET), ("]", TokenType.RBRACKET),
                               (":", TokenType.COLON), (".", TokenType.DOT), (",", TokenType.COMMA), ("@", TokenType.AT)]:
                    if text.startswith(op):
                        self.tokens.append(Token(tt, op, line_num, col))
                        text = text[len(op):]; col += len(op); matched = True; break
                if not matched:
                    self.engine.report(ErrorCodes.UNEXPECTED_CHAR, Severity.ERROR, f"Unexpected character: '{char}'", line_num, col)
                    raise AetherError(Diagnostic(ErrorCodes.UNEXPECTED_CHAR, Severity.ERROR, f"Unexpected character: '{char}'", line_num, col, self.engine.filename, self.engine.source))
                    
        self.tokens.append(Token(TokenType.NEWLINE, "\\n", line_num, col))