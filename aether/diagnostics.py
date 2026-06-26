# aether/diagnostics.py

import sys
import os

class Severity:
    ERROR = "ERROR"
    WARNING = "WARNING"
    NOTE = "NOTE"

class Diagnostic:
    """
    Represents a single compiler diagnostic (error or warning).
    Decoupled from the exception system so we can collect multiple errors.
    """
    def __init__(self, code, severity, message, line, col, filename, source, hint=None):
        self.code = code
        self.severity = severity
        self.message = message
        self.line = line
        self.col = col
        self.filename = filename
        self.source = source
        self.hint = hint

    def format(self) -> str:
        is_tty = hasattr(sys, 'stdout') and sys.stdout.isatty()
        RED = '\033[91m' if is_tty else ''
        YELLOW = '\033[93m' if is_tty else ''
        CYAN = '\033[96m' if is_tty else ''
        BOLD = '\033[1m' if is_tty else ''
        RESET = '\033[0m' if is_tty else ''
        
        color = RED if self.severity == Severity.ERROR else YELLOW
        
        header = f"{color}{BOLD}{self.severity.lower()}[E{self.code:03d}]{RESET}{BOLD}: {self.message}{RESET}"
        loc = f"{CYAN} -->{RESET} {self.filename}:{self.line}:{self.col}"
        
        lines = self.source.split('\n')
        source_line = lines[self.line - 1] if 0 < self.line <= len(lines) else ""
        
        line_num_str = str(self.line)
        padding = " " * len(line_num_str)
        gutter = f"{padding} {CYAN}|{RESET}"
        snippet = f"{line_num_str} {CYAN}|{RESET} {source_line}"
        
        underline_len = max(1, len(source_line) - self.col + 1)
        underline_spaces = " " * (self.col - 1)
        underline = "^" * underline_len
        underline_str = f"{padding} {CYAN}|{RESET} {underline_spaces}{color}{underline}{RESET} {self.message}"
        
        hint_str = ""
        if self.hint:
            hint_str = f"{padding} {CYAN}|{RESET}\n{padding} {CYAN}={RESET} {BOLD}hint:{RESET} {self.hint}"
            
        return f"{header}\n{loc}\n{gutter}\n{snippet}\n{underline_str}{hint_str}"

class DiagnosticEngine:
    """
    Collects diagnostics across the compilation pipeline.
    Allows the compiler to report multiple errors before halting.
    """
    def __init__(self, filename: str, source: str):
        self.filename = filename
        self.source = source
        self.diagnostics = []
        self.has_errors = False

    def report(self, code: int, severity: str, message: str, line: int, col: int, hint: str = None):
        diag = Diagnostic(code, severity, message, line, col, self.filename, self.source, hint)
        self.diagnostics.append(diag)
        if severity == Severity.ERROR:
            self.has_errors = True

    def print_diagnostics(self):
        for diag in self.diagnostics:
            print(diag.format())

class ErrorCodes:
    # Lexical (100s)
    UNEXPECTED_CHAR = 101
    UNTERMINATED_STRING = 102
    
    # Syntax (200s)
    UNEXPECTED_TOKEN = 201
    EXPECTED_TOKEN = 202
    INVALID_ASSIGNMENT = 203
    
    # Semantic (300s)
    UNDECLARED_VARIABLE = 301
    UNDECLARED_FUNCTION = 302
    DUPLICATE_DECLARATION = 303
    UNUSED_VARIABLE = 304
    SHADOWED_VARIABLE = 305
    
    # Type (400s)
    TYPE_MISMATCH = 401
    INVALID_OPERATION = 402
    INVALID_RETURN = 403
    
    # Codegen (500s)
    UNSUPPORTED_FEATURE = 501