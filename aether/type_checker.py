# aether/type_checker.py

from typing import Dict, List, Optional, Any
from .ast_nodes import *
from .diagnostics import DiagnosticEngine, Severity, ErrorCodes
from .symbol_table import SymbolTable

class TypeScope:
    def __init__(self, parent: Optional['TypeScope'] = None):
        self.parent = parent
        self.variables: Dict[str, str] = {}
    def declare(self, name: str, var_type: str) -> None: self.variables[name] = var_type
    def lookup(self, name: str) -> Optional[str]:
        if name in self.variables: return self.variables[name]
        return self.parent.lookup(name) if self.parent else None

class TypeChecker(Visitor):
    """
    Enforces strict typing and attaches type metadata to AST nodes.
    Decoupled from SemanticAnalyzer to ensure single-responsibility.
    """
    def __init__(self, ast: Program, function_table: Dict[str, Dict[str, Any]], classes: Dict[str, Dict[str, str]], engine: DiagnosticEngine):
        self.ast = ast
        self.functions = function_table
        self.classes = classes
        self.engine = engine
        self.global_scope = TypeScope()
        self.current_scope = self.global_scope
        self.current_function_return_type: Optional[str] = None

    def check(self) -> Program:
        self.ast.accept(self)
        return self.ast

    def visit_Program(self, node: Program) -> None:
        for s in node.statements: s.accept(self)
    def visit_NamespaceDecl(self, node: NamespaceDecl) -> None: pass
    def visit_ClassDecl(self, node: ClassDecl) -> None: pass

    def visit_FunctionDecl(self, node: FunctionDecl) -> None:
        p = self.current_scope; self.current_scope = TypeScope(p)
        old = self.current_function_return_type
        self.current_function_return_type = node.return_type.name if node.return_type else None
        for param in node.params: self.current_scope.declare(param.name, param.param_type.name)
        node.body.accept(self)
        self.current_scope = p; self.current_function_return_type = old

    def visit_Block(self, node: Block) -> None:
        p = self.current_scope; self.current_scope = TypeScope(p)
        for s in node.statements: s.accept(self)
        self.current_scope = p

    def visit_VariableDecl(self, node: VariableDecl) -> None:
        inf = node.value.accept(self)
        if node.var_type:
            exp = node.var_type.name
            if exp != inf: self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, f"Cannot assign '{inf}' to '{exp}'.", node.line, node.col)
        else: node.var_type = TypeNode(node.line, node.col, inf)
        node.inferred_type = node.var_type.name
        self.current_scope.declare(node.name, node.var_type.name)

    def visit_Assignment(self, node: Assignment) -> None:
        if isinstance(node.target, Identifier):
            t = self.current_scope.lookup(node.target.name)
            if not t: self.engine.report(ErrorCodes.UNDECLARED_VARIABLE, Severity.ERROR, f"Undeclared variable '{node.target.name}'.", node.line, node.col)
            node.target.inferred_type = t
        else:
            t = node.target.accept(self)
        v = node.value.accept(self)
        if t != v: self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, f"Cannot assign '{v}' to '{t}'.", node.line, node.col)

    def visit_CompoundAssign(self, node: CompoundAssign) -> None:
        node.target.accept(self); node.value.accept(self)

    def visit_IfStmt(self, node: IfStmt) -> None:
        if node.condition.accept(self) != "bool": self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, "If condition must be bool.", node.line, node.col)
        node.then_block.accept(self)
        for e in node.elifs: e.accept(self)
        if node.else_stmt: node.else_stmt.accept(self)

    def visit_ForStmt(self, node: ForStmt) -> None:
        if node.start.accept(self) != "int" or node.end.accept(self) != "int": self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, "For bounds must be int.", node.line, node.col)
        p = self.current_scope; self.current_scope = TypeScope(p)
        self.current_scope.declare(node.var_name, "int")
        node.body.accept(self)
        self.current_scope = p

    def visit_WhileStmt(self, node: WhileStmt) -> None:
        if node.condition.accept(self) != "bool": self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, "While condition must be bool.", node.line, node.col)
        node.body.accept(self)

    def visit_ReturnStmt(self, node: ReturnStmt) -> None:
        if self.current_function_return_type is None:
            if node.value: self.engine.report(ErrorCodes.INVALID_RETURN, Severity.ERROR, "Cannot return value from void function.", node.line, node.col)
        else:
            if not node.value: self.engine.report(ErrorCodes.INVALID_RETURN, Severity.ERROR, "Must return value.", node.line, node.col)
            if node.value.accept(self) != self.current_function_return_type: self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, "Return type mismatch.", node.line, node.col)

    def visit_ExprStmt(self, node: ExprStmt) -> None: node.expr.accept(self)
    
    def visit_Literal(self, node: Literal) -> str:
        if node.lit_type == "array":
            t = node.elements[0].accept(self) if node.elements else "int"
            node.inferred_type = f"{t}[]"
            return node.inferred_type
        node.inferred_type = node.lit_type
        return node.lit_type

    def visit_TupleLiteral(self, node: TupleLiteral) -> str:
        for e in node.elements: e.accept(self)
        node.inferred_type = "tuple"
        return "tuple"

    def visit_FormatString(self, node: FormatString) -> str:
        for p in node.parts:
            if not isinstance(p, str): p.accept(self)
        node.inferred_type = "string"
        return "string"

    def visit_Identifier(self, node: Identifier) -> str:
        t = self.current_scope.lookup(node.name)
        if not t: self.engine.report(ErrorCodes.UNDECLARED_VARIABLE, Severity.ERROR, f"Undeclared variable '{node.name}'.", node.line, node.col)
        node.inferred_type = t; return t

    def visit_MemberAccess(self, node: MemberAccess) -> str:
        obj_type = node.obj.accept(self)
        if obj_type not in self.classes: self.engine.report(ErrorCodes.INVALID_OPERATION, Severity.ERROR, f"Type '{obj_type}' has no members.", node.line, node.col)
        t = self.classes[obj_type][node.member]
        node.inferred_type = t; return t

    def visit_IndexAccess(self, node: IndexAccess) -> str:
        arr_type = node.array.accept(self)
        node.index.accept(self)
        t = arr_type[:-2]
        node.inferred_type = t; return t

    def visit_BinaryOp(self, node: BinaryOp) -> str:
        l = node.left.accept(self); r = node.right.accept(self)
        if l != r: self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, f"Type mismatch in binary op '{node.op}'.", node.line, node.col)
        t = "bool" if node.op in ["==", "!=", "<", ">", "<=", ">=", "&&", "||"] else "int"
        node.inferred_type = t; return t

    def visit_UnaryOp(self, node: UnaryOp) -> str:
        t = node.right.accept(self)
        if node.op == "-" and t != "int": self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, "Unary '-' requires int.", node.line, node.col)
        if node.op == "!" and t != "bool": self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, "Unary '!' requires bool.", node.line, node.col)
        node.inferred_type = t; return t

    def visit_FunctionCall(self, node: FunctionCall) -> Optional[str]:
        full_name = f"{node.namespace}::{node.name}" if node.namespace else node.name
        if full_name not in self.functions:
            node.inferred_type = None; return None
        sig = self.functions[full_name]
        for i, a in enumerate(node.args):
            a_type = a.accept(self)
            if a_type != sig["params"][i]: self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, f"Arg {i+1} type mismatch.", node.line, node.col)
        node.inferred_type = sig["return"]; return sig["return"]

    def visit_MethodCall(self, node: MethodCall) -> Optional[str]:
        obj_type = node.obj.accept(self)
        full_name = f"{obj_type}_{node.method}"
        if full_name not in self.functions: self.engine.report(ErrorCodes.UNDECLARED_FUNCTION, Severity.ERROR, f"Method '{node.method}' not found on '{obj_type}'.", node.line, node.col)
        sig = self.functions[full_name]
        for i, a in enumerate(node.args):
            a_type = a.accept(self)
            if a_type != sig["params"][i]: self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, f"Arg {i+1} type mismatch.", node.line, node.col)
        node.inferred_type = sig["return"]; return sig["return"]