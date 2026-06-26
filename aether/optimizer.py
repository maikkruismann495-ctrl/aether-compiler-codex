# aether/optimizer.py

import copy
import math
from typing import Optional, Any, List, Union
from .ast_nodes import *
from .diagnostics import DiagnosticEngine, Severity, ErrorCodes

class OptScope:
    def __init__(self, parent: Optional['OptScope'] = None):
        self.parent = parent
        self.consts = {}
        self.assigned = set()
    def declare_const(self, name: str, literal: Literal) -> None:
        if name not in self.assigned: self.consts[name] = literal
    def mark_assigned(self, name: str) -> None:
        self.assigned.add(name)
        if name in self.consts: del self.consts[name]
    def lookup_const(self, name: str) -> Optional[Literal]:
        if name in self.consts: return self.consts[name]
        return self.parent.lookup_const(name) if self.parent else None

class Optimizer(Visitor):
    """
    Performs AST-level optimizations: Constant Folding, Loop Unrolling, Dead Code Elimination.
    """
    def __init__(self, ast: Program, engine: DiagnosticEngine):
        self.ast = ast
        self.engine = engine
        self.global_scope = OptScope()
        self.current_scope = self.global_scope

    def optimize(self) -> Program: return self.ast.accept(self)

    def _make_literal(self, value: Any, lit_type: str, line: int, col: int) -> Literal:
        lit = Literal(line, col, value, lit_type)
        lit.inferred_type = lit_type
        return lit

    def _make_block(self, statements: List[ASTNode], line: int, col: int) -> Block:
        return Block(line, col, statements)

    def visit_Program(self, node: Program) -> Program:
        new_stmts = [s.accept(self) for s in node.statements if s.accept(self) is not None]
        return Program(node.line, node.col, new_stmts)

    def visit_NamespaceDecl(self, node: NamespaceDecl) -> NamespaceDecl: return node
    def visit_ClassDecl(self, node: ClassDecl) -> ClassDecl: return node

    def visit_FunctionDecl(self, node: FunctionDecl) -> FunctionDecl:
        p = self.current_scope; self.current_scope = OptScope(p)
        node.body = node.body.accept(self)
        self.current_scope = p
        return node

    def visit_Block(self, node: Block) -> Block:
        p = self.current_scope; self.current_scope = OptScope(p)
        new_statements = []
        for s in node.statements:
            opt = s.accept(self)
            if opt is not None: new_statements.append(opt)
        self.current_scope = p
        return self._make_block(new_statements, node.line, node.col)

    def visit_VariableDecl(self, node: VariableDecl) -> VariableDecl:
        node.value = node.value.accept(self)
        if isinstance(node.value, Literal): self.current_scope.declare_const(node.name, node.value)
        return node

    def visit_Assignment(self, node: Assignment) -> Assignment:
        node.value = node.value.accept(self)
        if isinstance(node.target, Identifier): self.current_scope.mark_assigned(node.target.name)
        return node

    def visit_CompoundAssign(self, node: CompoundAssign) -> CompoundAssign:
        node.value = node.value.accept(self)
        if isinstance(node.target, Identifier): self.current_scope.mark_assigned(node.target.name)
        return node

    def visit_IfStmt(self, node: IfStmt) -> Optional[ASTNode]:
        node.condition = node.condition.accept(self)
        if isinstance(node.condition, Literal) and node.condition.lit_type == "bool":
            if node.condition.value is True: return node.then_block.accept(self)
            elif node.condition.value is False:
                for eif in node.elifs: eif.accept(self)
                return node.else_stmt.accept(self) if node.else_stmt else None
        node.then_block = node.then_block.accept(self)
        for eif in node.elifs: eif.accept(self)
        if node.else_stmt: node.else_stmt = node.else_stmt.accept(self)
        return node

    def visit_ForStmt(self, node: ForStmt) -> ASTNode:
        start = node.start.accept(self); end = node.end.accept(self)
        if not isinstance(start, Literal) or not isinstance(end, Literal):
            self.engine.report(ErrorCodes.UNSUPPORTED_FEATURE, Severity.ERROR, "Compile-time loop bounds must evaluate to constant integers.", node.line, node.col)
            return node
        unrolled = []
        for i in range(start.value, end.value):
            p = self.current_scope; self.current_scope = OptScope(p)
            self.current_scope.declare_const(node.var_name, self._make_literal(i, "int", node.line, node.col))
            body_copy = copy.deepcopy(node.body)
            unrolled.append(body_copy.accept(self))
            self.current_scope = p
        return self._make_block(unrolled, node.line, node.col)

    def visit_WhileStmt(self, node: WhileStmt) -> WhileStmt:
        node.condition = node.condition.accept(self)
        node.body = node.body.accept(self)
        return node

    def visit_ReturnStmt(self, node: ReturnStmt) -> ReturnStmt:
        if node.value: node.value = node.value.accept(self)
        return node

    def visit_ExprStmt(self, node: ExprStmt) -> ExprStmt:
        node.expr = node.expr.accept(self); return node

    def visit_Literal(self, node: Literal) -> Literal: return node
    
    def visit_TupleLiteral(self, node: TupleLiteral) -> TupleLiteral:
        node.elements = [e.accept(self) for e in node.elements]
        return node

    def visit_FormatString(self, node: FormatString) -> ASTNode:
        new_parts = []
        for p in node.parts:
            if isinstance(p, str): new_parts.append(p)
            else:
                opt = p.accept(self)
                if isinstance(opt, Literal): new_parts.append(str(opt.value))
                else: new_parts.append(opt)
        if all(isinstance(p, str) for p in new_parts):
            merged = "".join(new_parts)
            return Literal(node.line, node.col, merged, "string")
        node.parts = new_parts
        return node

    def visit_Identifier(self, node: Identifier) -> ASTNode:
        c = self.current_scope.lookup_const(node.name)
        return copy.deepcopy(c) if c else node

    def visit_MemberAccess(self, node: MemberAccess) -> ASTNode:
        node.obj = node.obj.accept(self); return node
        
    def visit_IndexAccess(self, node: IndexAccess) -> ASTNode:
        node.array = node.array.accept(self); node.index = node.index.accept(self); return node

    def visit_BinaryOp(self, node: BinaryOp) -> ASTNode:
        l = node.left.accept(self); r = node.right.accept(self)
        node.left = l; node.right = r
        if isinstance(l, Literal) and isinstance(r, Literal): return self._fold_binary(node.op, l, r, node.line, node.col)
        return node

    def visit_UnaryOp(self, node: UnaryOp) -> ASTNode:
        r = node.right.accept(self); node.right = r
        if isinstance(r, Literal):
            if node.op == "-" and r.lit_type == "int": return self._make_literal(-r.value, "int", node.line, node.col)
            if node.op == "!" and r.lit_type == "bool": return self._make_literal(not r.value, "bool", node.line, node.col)
        return node

    def visit_FunctionCall(self, node: FunctionCall) -> ASTNode:
        node.args = [a.accept(self) for a in node.args]
        for k in node.kwargs: node.kwargs[k] = node.kwargs[k].accept(self)
        return node

    def visit_MethodCall(self, node: MethodCall) -> MethodCall:
        node.obj = node.obj.accept(self); node.args = [a.accept(self) for a in node.args]; return node

    def _fold_binary(self, op: str, l: Literal, r: Literal, line: int, col: int) -> Literal:
        lv, rv, lt = l.value, r.value, l.lit_type
        if lt == "int":
            if op == '+': return self._make_literal(lv + rv, "int", line, col)
            if op == '-': return self._make_literal(lv - rv, "int", line, col)
            if op == '*': return self._make_literal(lv * rv, "int", line, col)
            if op == '/': return self._make_literal(int(lv / rv) if rv != 0 else 0, "int", line, col)
            if op == '%': return self._make_literal(lv - (int(lv / rv) * rv) if rv != 0 else 0, "int", line, col)
            if op == '==': return self._make_literal(lv == rv, "bool", line, col)
            if op == '!=': return self._make_literal(lv != rv, "bool", line, col)
            if op == '<': return self._make_literal(lv < rv, "bool", line, col)
            if op == '>': return self._make_literal(lv > rv, "bool", line, col)
            if op == '<=': return self._make_literal(lv <= rv, "bool", line, col)
            if op == '>=': return self._make_literal(lv >= rv, "bool", line, col)
        if lt == "bool":
            if op == '&&': return self._make_literal(lv and rv, "bool", line, col)
            if op == '||': return self._make_literal(lv or rv, "bool", line, col)
            if op == '==': return self._make_literal(lv == rv, "bool", line, col)
            if op == '!=': return self._make_literal(lv != rv, "bool", line, col)
        if lt == "string":
            if op == '==': return self._make_literal(lv == rv, "bool", line, col)
            if op == '!=': return self._make_literal(lv != rv, "bool", line, col)
        self.engine.report(ErrorCodes.INVALID_OPERATION, Severity.ERROR, f"Cannot fold operator '{op}' for type '{lt}'.", line, col)
        return l