# src/aether/semantic.py

from typing import Dict, List, Optional, Any
from .ast_nodes import *
from .errors import SemanticError

class Scope:
    def __init__(self, parent=None):
        self.parent = parent
        self.vars: Dict[str, Dict[str, Any]] = {}
    def declare(self, name, t, line, col):
        if name in self.vars: raise SemanticError(f"Variable '{name}' already declared", line, col)
        self.vars[name] = {"type": t}
    def lookup(self, name):
        if name in self.vars: return self.vars[name]
        return self.parent.lookup(name) if self.parent else None

class SemanticAnalyzer(Visitor):
    def __init__(self, ast: Program):
        self.ast = ast
        self.scope = Scope()
        self.functions: Dict[str, Dict[str, Any]] = {
            "say": {"params": ["string"], "return": None},
            "give": {"params": ["string", "string", "int"], "return": None},
            "summon": {"params": ["string", "int", "int", "int"], "return": None},
            "particle": {"params": ["string", "int", "int", "int", "int", "int"], "return": None},
            "run": {"params": ["string"], "return": None},
            "time.sleep": {"params": ["int"], "return": None},
        }
        self.classes: Dict[str, Dict[str, str]] = {}
        self.ret_type: Optional[str] = None

    def analyze(self):
        self._collect(self.ast)
        self.ast.accept(self)
        return self.ast

    def _collect(self, node):
        if isinstance(node, Program):
            for s in node.statements: self._collect(s)
        elif isinstance(node, ClassDecl):
            self.classes[node.name] = node.fields
            for m in node.methods:
                self.functions[f"{node.name}_{m.name}"] = {"params": [p.param_type.name for p in m.params], "return": m.return_type.name if m.return_type else None}
        elif isinstance(node, FunctionDecl):
            self.functions[node.name] = {"params": [p.param_type.name for p in node.params], "return": node.return_type.name if node.return_type else None}

    def visit_NamespaceDecl(self, node): pass
    def visit_ClassDecl(self, node): pass

    def visit_FunctionDecl(self, node):
        p = self.scope; self.scope = Scope(p)
        old = self.ret_type
        self.ret_type = node.return_type.name if node.return_type else None
        for param in node.params: self.scope.declare(param.name, param.param_type.name, node.line, node.col)
        node.body.accept(self)
        self.scope = p; self.ret_type = old

    def visit_Block(self, node):
        p = self.scope; self.scope = Scope(p)
        for s in node.statements: s.accept(self)
        self.scope = p

    def visit_VariableDecl(self, node):
        t = node.value.accept(self)
        if node.var_type:
            if node.var_type.name != t: raise SemanticError(f"Cannot assign {t} to {node.var_type.name}", node.line, node.col)
        else: node.var_type = TypeNode(node.line, node.col, t)
        node.inferred_type = node.var_type.name
        self.scope.declare(node.name, node.var_type.name, node.line, node.col)

    def visit_Assignment(self, node):
        if not isinstance(node.target, (Identifier, MemberAccess, IndexAccess)): raise SemanticError("Invalid assignment target", node.line, node.col)
        t = node.target.accept(self)
        v = node.value.accept(self)
        if t != v: raise SemanticError(f"Cannot assign {v} to {t}", node.line, node.col)

    def visit_CompoundAssign(self, node):
        node.target.accept(self); node.value.accept(self)

    def visit_IfStmt(self, node):
        if node.condition.accept(self) != "bool": raise SemanticError("If condition must be bool", node.line, node.col)
        node.then_block.accept(self)
        for e in node.elifs: e.accept(self)
        if node.else_stmt: node.else_stmt.accept(self)

    def visit_ForStmt(self, node):
        if node.start.accept(self) != "int" or node.end.accept(self) != "int": raise SemanticError("For loop bounds must be int", node.line, node.col)
        p = self.scope; self.scope = Scope(p)
        self.scope.declare(node.var_name, "int", node.line, node.col)
        node.body.accept(self)
        self.scope = p

    def visit_WhileStmt(self, node):
        if node.condition.accept(self) != "bool": raise SemanticError("While condition must be bool", node.line, node.col)
        node.body.accept(self)

    def visit_ReturnStmt(self, node):
        if self.ret_type is None:
            if node.value: raise SemanticError("Cannot return value from void function", node.line, node.col)
        else:
            if not node.value: raise SemanticError("Must return value", node.line, node.col)
            if node.value.accept(self) != self.ret_type: raise SemanticError("Return type mismatch", node.line, node.col)

    def visit_ExprStmt(self, node): node.expr.accept(self)
    def visit_Literal(self, node): 
        if node.lit_type == "array": return "int[]" # MVP arrays are int
        return node.lit_type
    def visit_TupleLiteral(self, node): return "tuple"
    def visit_FormatString(self, node): 
        for p in node.parts:
            if not isinstance(p, str): p.accept(self)
        return "string"
    def visit_Identifier(self, node):
        v = self.scope.lookup(node.name)
        if not v: raise SemanticError(f"Undeclared variable '{node.name}'", node.line, node.col)
        node.inferred_type = v["type"]
        return v["type"]

    def visit_MemberAccess(self, node):
        t = node.obj.accept(self)
        if t not in self.classes: raise SemanticError(f"Type '{t}' has no members", node.line, node.col)
        if node.member not in self.classes[t]: raise SemanticError(f"Class '{t}' has no field '{node.member}'", node.line, node.col)
        node.inferred_type = self.classes[t][node.member]
        return self.classes[t][node.member]

    def visit_IndexAccess(self, node):
        t = node.array.accept(self)
        if not t.endswith("[]"): raise SemanticError(f"Cannot index type '{t}'", node.line, node.col)
        node.index.accept(self)
        node.inferred_type = t[:-2]
        return t[:-2]

    def visit_BinaryOp(self, node):
        l = node.left.accept(self); r = node.right.accept(self)
        if l != r: raise SemanticError(f"Type mismatch in binary op '{node.op}'", node.line, node.col)
        node.inferred_type = "bool" if node.op in ["==", "!=", "<", ">", "<=", ">=", "&&", "||"] else "int"
        return node.inferred_type

    def visit_UnaryOp(self, node):
        t = node.right.accept(self)
        if node.op == "-" and t != "int": raise SemanticError("Unary '-' requires int", node.line, node.col)
        if node.op == "!" and t != "bool": raise SemanticError("Unary '!' requires bool", node.line, node.col)
        node.inferred_type = t
        return t

    def visit_FunctionCall(self, node):
        if node.name not in self.functions: return None # Allow native commands
        sig = self.functions[node.name]
        for i, a in enumerate(node.args):
            if a.accept(self) != sig["params"][i]: raise SemanticError(f"Arg {i+1} type mismatch", node.line, node.col)
        node.inferred_type = sig["return"]
        return sig["return"]

    def visit_MethodCall(self, node):
        t = node.obj.accept(self)
        full = f"{t}_{node.method}"
        if full not in self.functions: raise SemanticError(f"Method '{node.method}' not found on '{t}'", node.line, node.col)
        sig = self.functions[full]
        for i, a in enumerate(node.args):
            if a.accept(self) != sig["params"][i]: raise SemanticError(f"Arg {i+1} type mismatch", node.line, node.col)
        node.inferred_type = sig["return"]
        return sig["return"]