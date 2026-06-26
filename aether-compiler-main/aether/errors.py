# aether/errors.py

from .diagnostics import Diagnostic, Severity, ErrorCodes

class AetherError(Exception):
    """Base exception for all Aether compiler errors."""
    def __init__(self, diag: Diagnostic):
        self.diag = diag
        super().__init__(diag.format())

# Helper functions to create specific errors easily
def make_error(code, message, line, col, filename, source, hint=None):
    diag = Diagnostic(code, Severity.ERROR, message, line, col, filename, source, hint)
    return AetherError(diag)

def make_syntax_error(message, line, col, filename, source, hint=None):
    return make_error(ErrorCodes.UNEXPECTED_TOKEN, message, line, col, filename, source, hint)

def make_type_error(message, line, col, filename, source, hint=None):
    return make_error(ErrorCodes.TYPE_MISMATCH, message, line, col, filename, source, hint)

def make_semantic_error(code, message, line, col, filename, source, hint=None):
    return make_error(code, message, line, col, filename, source, hint)