from dataclasses import dataclass
from typing import List, Optional, Any

@dataclass
class Node:
    """Base class for all AST nodes"""
    pass

@dataclass
class Expr(Node):
    """Base class for all expressions"""
    pass

@dataclass
class Stmt(Node):
    """Base class for all statements"""
    pass

@dataclass
class Program(Node):
    declarations: List[Stmt]

@dataclass
class VarDecl(Stmt):
    name: str
    initializer: Expr

@dataclass
class FunDecl(Stmt):
    name: str
    params: List[str]
    return_type: Optional[str]
    body: List[Stmt]

@dataclass
class ExpressionStmt(Stmt):
    expression: Expr

@dataclass
class BinaryExpr(Expr):
    left: Expr
    operator: str
    right: Expr

@dataclass
class UnaryExpr(Expr):
    operator: str
    right: Expr

@dataclass
class GroupingExpr(Expr):
    expression: Expr

@dataclass
class Literal(Expr):
    value: Any

@dataclass
class Identifier(Expr):
    name: str

@dataclass
class AssignExpr(Expr):
    name: Identifier
    value: Expr

@dataclass
class CallExpr(Expr):
    callee: Expr
    arguments: List[Expr]

@dataclass
class ReturnStmt(Stmt):
    value: Optional[Expr]

@dataclass
class IfStmt(Stmt):
    condition: Expr
    then_branch: List[Stmt]
    else_branch: Optional[List[Stmt]] = None

@dataclass
class WhileStmt(Stmt):
    condition: Expr
    body: List[Stmt]

@dataclass
class ErrorStmt(Stmt):
    """Representa un error sintáctico"""
    message: str
    line: int
    column: int

@dataclass
class IndentationError(ErrorStmt):
    """Error específico de indentación"""
    expected_indent: int
    actual_indent: int

@dataclass
class DelimiterError(ErrorStmt):
    """Error de delimitadores (paréntesis, dos puntos, etc)"""
    expected: str
    found: Optional[str] 