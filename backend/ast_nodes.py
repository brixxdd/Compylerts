from dataclasses import dataclass
from typing import List, Optional, Any

@dataclass
class Node:
    """Base class for all AST nodes"""
    pass

@dataclass
class Expression(Node):
    """Base class for all expressions"""
    pass

@dataclass
class Statement(Node):
    """Base class for all statements"""
    pass

@dataclass
class Literal(Expression):
    value: Any

@dataclass
class Identifier(Expression):
    name: str

@dataclass
class BinaryExpr(Expression):
    left: Expression
    operator: str
    right: Expression

@dataclass
class UnaryExpr(Expression):
    operator: str
    right: Expression

@dataclass
class CallExpr(Expression):
    callee: Expression
    arguments: List[Expression]

@dataclass
class AssignExpr(Expression):
    name: Identifier
    value: Expression

@dataclass
class ExpressionStmt(Statement):
    expression: Expression

@dataclass
class VariableDecl(Statement):
    name: str
    type_hint: Optional[str] = None
    initializer: Optional[Expression] = None

@dataclass
class FunctionDecl(Statement):
    name: str
    params: List[VariableDecl]
    return_type: Optional[str]
    body: List[Statement]

@dataclass
class ReturnStmt(Statement):
    value: Optional[Expression] = None

@dataclass
class IfStmt(Statement):
    condition: Expression
    then_branch: List[Statement]
    else_branch: Optional[List[Statement]] = None

@dataclass
class WhileStmt(Statement):
    condition: Expression
    body: List[Statement]

@dataclass
class Program(Node):
    statements: List[Statement] 