from dataclasses import dataclass
from typing import List, Optional, Any
from enum import Enum, auto

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
    type_name: str  # 'number', 'string', 'boolean', 'fstring', etc.
    
    @property
    def is_fstring(self):
        return self.type_name == 'fstring'

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
class ForStmt(Stmt):
    variable: Identifier
    iterable: Expr
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

@dataclass
class ArgumentError(ErrorStmt):
    """Error específico de argumentos en llamadas a funciones"""
    function_name: str
    expected_args: int
    found_args: int

@dataclass
class TrailingCommaError(ErrorStmt):
    """Error específico para comas huérfanas en llamadas a funciones"""
    function_name: str
    line: int
    column: int
    example: str

    def __str__(self):
        return f"""Error en línea {self.line}: Coma huérfana en llamada a función '{self.function_name}'
En el código:
    {self.example}
    {' ' * self.column}^ No se permiten comas sin argumentos
Sugerencia: Agrega un argumento después de la coma o elimina la coma"""

# Enumeraciones para operadores
class BinaryOp(Enum):
    PLUS = auto()
    MINUS = auto()
    MULTIPLY = auto()
    DIVIDE = auto()
    MODULO = auto()
    EQUAL = auto()
    NOT_EQUAL = auto()
    LESS = auto()
    GREATER = auto()
    LESS_EQUAL = auto()
    GREATER_EQUAL = auto()

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

class WhileStmt(Statement):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

class ForStmt(Statement):
    def __init__(self, variable, iterable, body):
        self.variable = variable  # Nombre de la variable iteradora
        self.iterable = iterable  # Expresión a iterar
        self.body = body          # Lista de statements dentro del bucle

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

def p_arguments(self, p):
    '''arguments : expression
                | arguments COMMA expression
                | STRING
                | arguments COMMA STRING'''
    if len(p) == 2:
        # Si es una expresión o string simple
        p[0] = [p[1] if isinstance(p[1], Literal) else Literal(p[1], 'string' if isinstance(p[1], str) else 'any')]
    else:
        # Si es una lista de argumentos con coma
        p[0] = p[1] + [p[3] if isinstance(p[3], Literal) else Literal(p[3], 'string' if isinstance(p[3], str) else 'any')] 

def print_ast(node, indent=0):
    """Imprime el AST de forma legible"""
    prefix = "  " * indent
    
    if isinstance(node, Program):
        print(f"{prefix}Program")
        for stmt in node.statements:
            print_ast(stmt, indent + 1)
    
    elif isinstance(node, FunctionDef):
        print(f"{prefix}FunctionDef: {node.name}")
        params_str = []
        for p in node.params:
            type_name = p.type.name if p.type else "any"
            params_str.append(f"{p.name}: {type_name}")
        print(f"{prefix}  Parameters: {params_str}")
        print(f"{prefix}  Return Type: {node.return_type}")
        print(f"{prefix}  Body:")
        for stmt in node.body:
            print_ast(stmt, indent + 2)
    
    elif isinstance(node, ReturnStmt):
        print(f"{prefix}Return:")
        if node.value:
            print_ast(node.value, indent + 1)
    
    elif isinstance(node, AssignmentStmt):
        print(f"{prefix}Assignment:")
        print(f"{prefix}  Target: {node.target.name}")
        print(f"{prefix}  Value:", end=" ")
        print_ast(node.value, 0)
        print()  # Nueva línea después del valor
    
    elif isinstance(node, ExpressionStmt):
        print(f"{prefix}ExpressionStmt:")
        if hasattr(node, 'expression'):
            print(f"{prefix}  Expression:", end=" ")
            print_ast(node.expression, 0)
            print()
    
    elif isinstance(node, CallExpr):
        if hasattr(node, 'callee') and hasattr(node.callee, 'name'):
            print(f"CallExpr: {node.callee.name}(", end="")
            args = []
            for arg in node.arguments:
                if isinstance(arg, Literal):
                    args.append(f"{arg.value}")
                elif isinstance(arg, Identifier):
                    args.append(f"{arg.name}")
                else:
                    args.append(str(arg))
            print(", ".join(args), end="")
            print(")")
        else:
            print(f"CallExpr: <unknown>")
    
    elif isinstance(node, IfStmt):
        print(f"{prefix}IfStmt:")
        print(f"{prefix}  Condition:", end=" ")
        print_ast(node.condition, 0)
        print()
        print(f"{prefix}  Then:")
        for stmt in node.then_branch:
            print_ast(stmt, indent + 2)
        if node.else_branch:
            print(f"{prefix}  Else:")
            for stmt in node.else_branch:
                print_ast(stmt, indent + 2)
    
    elif isinstance(node, ForStmt):
        print(f"{prefix}ForStmt:")
        print(f"{prefix}  Variable: {node.variable.name}")
        print(f"{prefix}  Iterable:", end=" ")
        print_ast(node.iterable, 0)
        print()
        print(f"{prefix}  Body:")
        for stmt in node.body:
            print_ast(stmt, indent + 2)
    
    elif isinstance(node, WhileStmt):
        print(f"{prefix}WhileStmt:")
        print(f"{prefix}  Condition:", end=" ")
        print_ast(node.condition, 0)
        print()
        print(f"{prefix}  Body:")
        for stmt in node.body:
            print_ast(stmt, indent + 2)
    
    elif isinstance(node, BinaryExpr):
        print(f"BinaryExpr: {node.operator}")
        print(f"{prefix}  Left:", end=" ")
        print_ast(node.left, 0)
        print()
        print(f"{prefix}  Right:", end=" ")
        print_ast(node.right, 0)
    
    elif isinstance(node, Literal):
        if hasattr(node, 'type_name'):
            print(f"Literal({repr(node.value)}: {node.type_name})", end="")
        else:
            print(f"Literal({repr(node.value)})", end="")
    
    elif isinstance(node, Identifier):
        print(f"Identifier({node.name})", end="")
    
    else:
        print(f"{prefix}Unknown node type: {type(node)}") 