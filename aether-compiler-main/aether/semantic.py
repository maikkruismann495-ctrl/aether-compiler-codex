# aether/semantic.py
import re
from typing import Dict, List, Optional, Any
from .ast_nodes import *
from .diagnostics import DiagnosticEngine, Severity, ErrorCodes
from .symbol_table import SymbolTable

class SemanticAnalyzer(Visitor):
    def __init__(self, ast: Program, engine: DiagnosticEngine):
        self.ast = ast
        self.engine = engine
        self.symbol_table = SymbolTable(engine)
        self.functions: Dict[str, Dict[str, Any]] = {}
        self.ret_type: Optional[str] = None

    def analyze(self):
        self._collect(self.ast)
        self.ast.accept(self)
        return self.ast

    def visit_Program(self, node):
        for s in node.statements:
            s.accept(self)

    def _collect(self, node):
        if isinstance(node, Program):
            for s in node.statements: self._collect(s)
        elif isinstance(node, FunctionDecl):
            if node.name in self.functions:
                self.engine.report(ErrorCodes.DUPLICATE_DECLARATION, Severity.ERROR, f"Function '{node.name}' is already defined", node.line, node.col)
            self.functions[node.name] = {"params": [p.param_type.name for p in node.params], "return": node.return_type.name if node.return_type else None}

    def visit_NamespaceDecl(self, node): pass

    def visit_FunctionDecl(self, node):
        self.symbol_table.push_scope(f"func_{node.name}")
        old = self.ret_type
        self.ret_type = node.return_type.name if node.return_type else None
        for param in node.params: 
            self.symbol_table.declare(param.name, param.param_type.name, param.line, param.col)
        node.body.accept(self)
        self.symbol_table.pop_scope()
        self.ret_type = old

    def visit_Block(self, node):
        self.symbol_table.push_scope("block")
        for s in node.statements: s.accept(self)
        self.symbol_table.pop_scope()

    def visit_VariableDecl(self, node):
        t = node.value.accept(self)
        if node.var_type:
            if node.var_type.name != t:
                self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, f"Cannot assign {t} to {node.var_type.name}", node.line, node.col)
        else: node.var_type = TypeNode(node.line, node.col, t)
        node.inferred_type = node.var_type.name
        self.symbol_table.declare(node.name, node.var_type.name, node.line, node.col, not node.is_mut)

    def visit_Assignment(self, node):
        if not isinstance(node.target, (Identifier, IndexAccess)):
            self.engine.report(ErrorCodes.INVALID_ASSIGNMENT, Severity.ERROR, "Invalid assignment target", node.line, node.col)
        if isinstance(node.target, Identifier):
            sym = self.symbol_table.lookup(node.target.name)
            if sym and sym.is_const:
                self.engine.report(ErrorCodes.INVALID_ASSIGNMENT, Severity.ERROR, f"Cannot assign to const variable '{node.target.name}'", node.line, node.col)
        t = node.target.accept(self)
        v = node.value.accept(self)
        if t != v: self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, f"Cannot assign {v} to {t}", node.line, node.col)

    def visit_CompoundAssign(self, node):
        if isinstance(node.target, Identifier):
            sym = self.symbol_table.lookup(node.target.name)
            if sym and sym.is_const:
                self.engine.report(ErrorCodes.INVALID_ASSIGNMENT, Severity.ERROR, f"Cannot assign to const variable '{node.target.name}'", node.line, node.col)
        node.target.accept(self); node.value.accept(self)

    def visit_IfStmt(self, node):
        if node.condition is not None:
            if node.condition.accept(self) != "bool":
                self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, "If condition must be bool", node.line, node.col)
        node.then_block.accept(self)
        if node.else_stmt: node.else_stmt.accept(self)

    def visit_ExecuteStmt(self, node):
        node.body.accept(self)

    def visit_ForStmt(self, node):
        if node.start.accept(self) != "int" or node.end.accept(self) != "int":
            self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, "For loop bounds must be int", node.line, node.col)
        self.symbol_table.push_scope("for_loop")
        self.symbol_table.declare(node.var_name, "int", node.line, node.col)
        node.body.accept(self)
        self.symbol_table.pop_scope()

    def visit_ReturnStmt(self, node):
        if self.ret_type is None:
            if node.value: self.engine.report(ErrorCodes.INVALID_RETURN, Severity.ERROR, "Cannot return value from void function", node.line, node.col)
        else:
            if not node.value: self.engine.report(ErrorCodes.INVALID_RETURN, Severity.ERROR, "Must return value", node.line, node.col)
            elif node.value.accept(self) != self.ret_type: self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, "Return type mismatch", node.line, node.col)

    def visit_RawCommandStmt(self, node):
        for name in re.findall(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}', node.cmd_str):
            self.symbol_table.lookup(name)
    def visit_ExprStmt(self, node): node.expr.accept(self)
    
    def visit_Literal(self, node): 
        if node.lit_type == "array": return "int[]"
        return node.lit_type
        
    def visit_ArrayLiteral(self, node): 
        t = node.elements[0].accept(self) if node.elements else "int"
        for e in node.elements[1:]:
            et = e.accept(self)
            if et != t:
                self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, f"Array element type '{et}' does not match '{t}'", e.line, e.col)
        return f"{t}[]"
        
    def visit_Identifier(self, node):
        sym = self.symbol_table.lookup(node.name)
        if not sym:
            self.engine.report(ErrorCodes.UNDECLARED_VARIABLE, Severity.ERROR, f"Undeclared variable '{node.name}'", node.line, node.col)
            return "unknown"
        node.inferred_type = sym.type
        return sym.type

    def visit_IndexAccess(self, node):
        t = node.array.accept(self)
        idx_t = node.index.accept(self)
        if idx_t != "int":
            self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, "Array index must be int", node.index.line, node.index.col)
        if not t or not t.endswith("[]"):
            self.engine.report(ErrorCodes.INVALID_OPERATION, Severity.ERROR, f"Cannot index type '{t}'", node.line, node.col)
            return "unknown"
        node.inferred_type = t[:-2]
        return t[:-2]

    def visit_BinaryOp(self, node):
        l = node.left.accept(self); r = node.right.accept(self)
        if l != r:
            self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, f"Type mismatch in binary op '{node.op}'", node.line, node.col)
        node.inferred_type = "bool" if node.op in ["==", "!=", "<", ">", "<=", ">=", "&&", "||"] else "int"
        return node.inferred_type

    def visit_UnaryOp(self, node):
        t = node.right.accept(self)
        if node.op == "-" and t != "int": self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, "Unary '-' requires int", node.line, node.col)
        if node.op == "!" and t != "bool": self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, "Unary '!' requires bool", node.line, node.col)
        node.inferred_type = t
        return t

    def visit_FunctionCall(self, node):
        if node.name not in self.functions:
            self.engine.report(ErrorCodes.UNDECLARED_FUNCTION, Severity.ERROR, f"Undeclared function '{node.name}'", node.line, node.col)
            return None
        sig = self.functions[node.name]
        if len(node.args) != len(sig["params"]):
            self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, f"Function '{node.name}' expects {len(sig['params'])} args, got {len(node.args)}", node.line, node.col)
            return sig["return"]
        for i, a in enumerate(node.args):
            a_type = a.accept(self)
            if a_type != sig["params"][i]:
                self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, f"Arg {i+1} type mismatch", node.line, node.col)
        node.inferred_type = sig["return"]
        return sig["return"]
