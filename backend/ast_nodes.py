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

# Enumeraciones para operadores
class BinaryOp:
    ADD = '+'
    SUBTRACT = '-'
    MULTIPLY = '*'
    DIVIDE = '/'
    MODULO = '%'
    EQUAL = '=='
    NOT_EQUAL = '!='
    LESS_THAN = '<'
    GREATER_THAN = '>'
    LESS_EQUAL = '<='
    GREATER_EQUAL = '>='

class UnaryOp:
    NEGATE = '-'

# Nodo base
class ASTNode:
    pass

# Nodo raíz del programa
class Program(ASTNode):
    def __init__(self, statements):
        self.statements = statements

# Declaraciones
class Statement(ASTNode):
    pass

class ExpressionStmt(Statement):
    def __init__(self, expression):
        self.expression = expression

class AssignmentStmt(Statement):
    def __init__(self, target, value):
        self.target = target
        self.value = value

class ReturnStmt(Statement):
    def __init__(self, value):
        self.value = value

class FunctionDef(Statement):
    def __init__(self, name, params, return_type, body):
        self.name = name
        self.params = params
        self.return_type = return_type
        self.body = body

class IfStmt(Statement):
    def __init__(self, condition, then_branch, else_branch):
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch

# Expresiones
class Expression(ASTNode):
    pass

class BinaryExpr(Expression):
    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator
        self.right = right

class UnaryExpr(Expression):
    def __init__(self, operator, operand):
        self.operator = operator
        self.operand = operand

class GroupingExpr(Expression):
    def __init__(self, expression):
        self.expression = expression

class Literal(Expression):
    def __init__(self, value):
        self.value = value

class Identifier(Expression):
    def __init__(self, name):
        self.name = name

class CallExpr(Expression):
    def __init__(self, callee, arguments):
        self.callee = callee
        self.arguments = arguments

# Parámetros y tipos
class Parameter(ASTNode):
    def __init__(self, name, type):
        self.name = name
        self.type = type

class Type(ASTNode):
    def __init__(self, name):
        self.name = name 