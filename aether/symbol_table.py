# aether/symbol_table.py

from typing import Dict, List, Optional, Any
from .diagnostics import DiagnosticEngine, Severity, ErrorCodes

class Symbol:
    def __init__(self, name: str, type: str, line: int, col: int, is_const: bool = False):
        self.name = name
        self.type = type
        self.line = line
        self.col = col
        self.is_const = is_const
        self.is_used = False
        self.is_mut = not is_const

class Scope:
    """
    Represents a lexical scope. 
    Supports nested scopes and shadowing detection.
    """
    def __init__(self, parent: Optional['Scope'] = None, scope_name: str = "global"):
        self.parent = parent
        self.scope_name = scope_name
        self.symbols: Dict[str, Symbol] = {}

    def declare(self, name: str, type: str, line: int, col: int, engine: DiagnosticEngine, is_const: bool = False) -> Symbol:
        if name in self.symbols:
            engine.report(
                ErrorCodes.DUPLICATE_DECLARATION, Severity.ERROR,
                f"Variable '{name}' is already declared in this scope",
                line, col, hint=f"Previous declaration was at line {self.symbols[name].line}"
            )
        if self.parent and self.parent.lookup(name):
            engine.report(
                ErrorCodes.SHADOWED_VARIABLE, Severity.WARNING,
                f"Variable '{name}' shadows an outer scope variable",
                line, col
            )
        sym = Symbol(name, type, line, col, is_const)
        self.symbols[name] = sym
        return sym

    def lookup(self, name: str) -> Optional[Symbol]:
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

class SymbolTable:
    """
    Manages the global scope and current execution scope.
    """
    def __init__(self, engine: DiagnosticEngine):
        self.engine = engine
        self.global_scope = Scope(None, "global")
        self.current_scope = self.global_scope

    def push_scope(self, name: str):
        new_scope = Scope(self.current_scope, name)
        self.current_scope = new_scope

    def pop_scope(self):
        for sym_name, sym in self.current_scope.symbols.items():
            if not sym.is_used:
                self.engine.report(
                    ErrorCodes.UNUSED_VARIABLE, Severity.WARNING,
                    f"Unused variable '{sym_name}'",
                    sym.line, sym.col
                )
        self.current_scope = self.current_scope.parent

    def declare(self, name: str, type: str, line: int, col: int, is_const: bool = False):
        return self.current_scope.declare(name, type, line, col, self.engine, is_const)

    def lookup(self, name: str) -> Optional[Symbol]:
        sym = self.current_scope.lookup(name)
        if sym:
            sym.is_used = True
        return sym