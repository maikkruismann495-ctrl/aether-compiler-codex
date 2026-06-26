# src/aether/errors.py

class AetherError(Exception):
    """Base exception for all Aether compiler errors."""
    pass

class LexError(AetherError):
    def __init__(self, message: str, line: int, col: int):
        self.message = message; self.line = line; self.col = col
        super().__init__(f"[LexError] at L{line}:C{col} -> {message}")

class ParseError(AetherError):
    def __init__(self, message: str, line: int, col: int):
        self.message = message; self.line = line; self.col = col
        super().__init__(f"[ParseError] at L{line}:C{col} -> {message}")

class SemanticError(AetherError):
    def __init__(self, message: str, line: int, col: int):
        self.message = message; self.line = line; self.col = col
        super().__init__(f"[SemanticError] at L{line}:C{col} -> {message}")

class TypeError(AetherError):
    def __init__(self, message: str, line: int, col: int):
        self.message = message; self.line = line; self.col = col
        super().__init__(f"[TypeError] at L{line}:C{col} -> {message}")

class CodegenError(AetherError):
    def __init__(self, message: str, line: int, col: int):
        self.message = message; self.line = line; self.col = col
        super().__init__(f"[CodegenError] at L{line}:C{col} -> {message}")