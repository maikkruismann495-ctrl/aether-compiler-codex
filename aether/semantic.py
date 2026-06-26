# src/aether/semantic.py

from typing import Dict, List, Optional, Any
from .ast_nodes import *
from .diagnostics import DiagnosticEngine, Severity, ErrorCodes
from .symbol_table import SymbolTable

class SemanticAnalyzer(Visitor):
    def __init__(self, ast: Program, engine: DiagnosticEngine):
        self.ast = ast
        self.engine = engine
        self.symbol_table = SymbolTable(engine)
        self.functions: Dict[str, Dict[str, Any]] = {
            "say": {"params": ["string"], "return": None},
            "give": {"params": ["string", "string", "int"], "return": None},
            "summon": {"params": ["string", "int", "int", "int"], "return": None},
            "particle": {"params": ["string", "int", "int", "int", "int", "int"], "return": None},
            "run": {"params": ["string"], "return": None},
            "wait": {"params": ["int"], "return": None},
            "entity": {"params": ["string"], "return": "Entity"},
            "time.sleep": {"params": ["int"], "return": None},
        }
        self.classes: Dict[str, Dict[str, str]] = {
            "Entity": {"selector": "string"}
        }
        self.ret_type: Optional[str] = None

    def analyze(self):
        self._collect(self.ast)
        self.ast.accept(self)
        return self.ast

    def _collect(self, node):
        if isinstance(node, Program):
            for s in node.statements: self._collect(s)
        elif isinstance(node, ClassDecl):
            if node.name in self.classes:
                self.engine.report(ErrorCodes.DUPLICATE_DECLARATION, Severity.ERROR, f"Class '{node.name}' is already defined", node.line, node.col)
            self.classes[node.name] = node.fields
            for m in node.methods:
                self.functions[f"{node.name}_{m.name}"] = {"params": [p.param_type.name for p in m.params], "return": m.return_type.name if m.return_type else None}
        elif isinstance(node, FunctionDecl):
            if node.name in self.functions:
                self.engine.report(ErrorCodes.DUPLICATE_DECLARATION, Severity.ERROR, f"Function '{node.name}' is already defined", node.line, node.col)
            self.functions[node.name] = {"params": [p.param_type.name for p in node.params], "return": node.return_type.name if node.return_type else None}

    def visit_NamespaceDecl(self, node): pass
    def visit_ClassDecl(self, node): pass

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
        self.symbol_table.declare(node.name, node.var_type.name, node.line, node.col)

    def visit_Assignment(self, node):
        if not isinstance(node.target, (Identifier, MemberAccess, IndexAccess)):
            self.engine.report(ErrorCodes.INVALID_ASSIGNMENT, Severity.ERROR, "Invalid assignment target", node.line, node.col)
        t = node.target.accept(self)
        v = node.value.accept(self)
        if t != v: self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, f"Cannot assign {v} to {t}", node.line, node.col)

    def visit_CompoundAssign(self, node):
        node.target.accept(self); node.value.accept(self)

    def visit_IfStmt(self, node):
        if node.condition.accept(self) != "bool":
            self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, "If condition must be bool", node.line, node.col)
        node.then_block.accept(self)
        for e in node.elifs: e.accept(self)
        if node.else_stmt: node.else_stmt.accept(self)

    def visit_ForStmt(self, node):
        if node.start.accept(self) != "int" or node.end.accept(self) != "int":
            self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, "For loop bounds must be int", node.line, node.col)
        self.symbol_table.push_scope("for_loop")
        self.symbol_table.declare(node.var_name, "int", node.line, node.col)
        node.body.accept(self)
        self.symbol_table.pop_scope()

    def visit_WhileStmt(self, node):
        if node.condition.accept(self) != "bool":
            self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, "While condition must be bool", node.line, node.col)
        node.body.accept(self)

    def visit_ExecuteStmt(self, node):
        for sub, sel in node.chain:
            sel.accept(self)
        node.body.accept(self)

    def visit_ReturnStmt(self, node):
        if self.ret_type is None:
            if node.value: self.engine.report(ErrorCodes.INVALID_RETURN, Severity.ERROR, "Cannot return value from void function", node.line, node.col)
        else:
            if not node.value: self.engine.report(ErrorCodes.INVALID_RETURN, Severity.ERROR, "Must return value", node.line, node.col)
            if node.value.accept(self) != self.ret_type: self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, "Return type mismatch", node.line, node.col)

    def visit_ExprStmt(self, node): node.expr.accept(self)
    
    def visit_Literal(self, node): 
        if node.lit_type == "array": return "int[]"
        return node.lit_type
        
    def visit_TupleLiteral(self, node): return "tuple"
    def visit_DictLiteral(self, node): 
        for v in node.elements.values(): v.accept(self)
        return "nbt"
        
    def visit_FormatString(self, node): 
        for p in node.parts:
            if not isinstance(p, str): p.accept(self)
        return "string"
        
    def visit_Identifier(self, node):
        sym = self.symbol_table.lookup(node.name)
        if not sym:
            self.engine.report(ErrorCodes.UNDECLARED_VARIABLE, Severity.ERROR, f"Undeclared variable '{node.name}'", node.line, node.col)
            return "unknown"
        node.inferred_type = sym.type
        return sym.type

    def visit_MemberAccess(self, node):
        t = node.obj.accept(self)
        if t not in self.classes:
            self.engine.report(ErrorCodes.INVALID_OPERATION, Severity.ERROR, f"Type '{t}' has no members", node.line, node.col)
            return "unknown"
        if node.member not in self.classes[t]:
            self.engine.report(ErrorCodes.UNDECLARED_VARIABLE, Severity.ERROR, f"Class '{t}' has no field '{node.member}'", node.line, node.col)
            return "unknown"
        node.inferred_type = self.classes[t][node.member]
        return self.classes[t][node.member]

    def visit_IndexAccess(self, node):
        t = node.array.accept(self)
        node.index.accept(self)
        if not t.endswith("[]"):
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
        if node.name not in self.functions: return None
        sig = self.functions[node.name]
        for i, a in enumerate(node.args):
            a_type = a.accept(self)
            if a_type != sig["params"][i]:
                self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, f"Arg {i+1} type mismatch", node.line, node.col)
        node.inferred_type = sig["return"]
        return sig["return"]

    def visit_MethodCall(self, node):
        t = node.obj.accept(self)
        # For Entity wrapper, we don't require explicit method definitions in the functions dict for MVP
        if t == "Entity":
            node.inferred_type = None
            return None
            
        full = f"{t}_{node.method}"
        if full not in self.functions:
            self.engine.report(ErrorCodes.UNDECLARED_FUNCTION, Severity.ERROR, f"Method '{node.method}' not found on '{t}'", node.line, node.col)
            return None
        sig = self.functions[full]
        for i, a in enumerate(node.args):
            a_type = a.accept(self)
            if a_type != sig["params"][i]:
                self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, f"Arg {i+1} type mismatch", node.line, node.col)
        node.inferred_type = sig["return"]
        return sig["return"]