# aether/ast_nodes.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Union, Any, Dict

@dataclass
class ASTNode:
    line: int; col: int
    def accept(self, visitor: 'Visitor') -> Any:
        method_name = f'visit_{type(self).__name__}'
        visitor_method = getattr(visitor, method_name, None)
        if visitor_method is not None: return visitor_method(self)
        if hasattr(visitor, 'generic_visit'): return visitor.generic_visit(self)
        raise NotImplementedError(f"No visit_{type(self).__name__} in {type(visitor).__name__}")

class Visitor:
    def generic_visit(self, node: ASTNode) -> Any: pass

@dataclass
class Program(ASTNode):
    statements: List[ASTNode]

@dataclass
class NamespaceDecl(ASTNode):
    name: str

@dataclass
class FunctionDecl(ASTNode):
    name: str
    params: List['Param']
    return_type: Optional['TypeNode']
    body: 'Block'

@dataclass
class Param(ASTNode):
    name: str; param_type: 'TypeNode'

@dataclass
class TypeNode(ASTNode):
    name: str

@dataclass
class Block(ASTNode):
    statements: List[ASTNode]

@dataclass
class VariableDecl(ASTNode):
    name: str; var_type: Optional[TypeNode]; value: ASTNode; is_mut: bool

@dataclass
class Assignment(ASTNode):
    target: ASTNode; value: ASTNode

@dataclass
class CompoundAssign(ASTNode):
    target: ASTNode; op: str; value: ASTNode

@dataclass
class IfStmt(ASTNode):
    condition: ASTNode; then_block: Block; else_stmt: Optional[Block]

@dataclass
class ForStmt(ASTNode):
    var_name: str; start: ASTNode; end: ASTNode; body: Block

@dataclass
class ReturnStmt(ASTNode):
    value: Optional[ASTNode]

@dataclass
class RawCommandStmt(ASTNode):
    cmd_str: str

@dataclass
class ExprStmt(ASTNode):
    expr: ASTNode

@dataclass
class Literal(ASTNode):
    value: Union[int, str, bool]; lit_type: str

@dataclass
class ArrayLiteral(ASTNode):
    elements: List[ASTNode]

@dataclass
class Identifier(ASTNode):
    name: str

@dataclass
class IndexAccess(ASTNode):
    array: ASTNode; index: ASTNode

@dataclass
class BinaryOp(ASTNode):
    left: ASTNode; op: str; right: ASTNode

@dataclass
class UnaryOp(ASTNode):
    op: str; right: ASTNode

@dataclass
class FunctionCall(ASTNode):
    name: str; args: List[ASTNode]