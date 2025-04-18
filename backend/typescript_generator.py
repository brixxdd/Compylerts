from ast_nodes import *
from typing import List, Dict

class TypeScriptGenerator:
    def __init__(self):
        self.output = []
        self.indentation = 0
        # Mapeo de tipos de Python a TypeScript
        self.type_mapping = {
            'int': 'number',
            'str': 'string',
            'float': 'number',
            'bool': 'boolean',
            'list': 'Array',
            'dict': 'Record',
            'None': 'void'
        }

    def generate(self, ast: Program) -> str:
        """Genera código TypeScript a partir del AST"""
        if ast is None:
            return ""
        self.output = []  # Reiniciar la salida
        self.visit_program(ast)
        return '\n'.join(self.output)

    def emit(self, code: str):
        """Emite una línea de código con la indentación correcta"""
        self.output.append('  ' * self.indentation + code)

    def visit_program(self, node: Program):
        """Visita el nodo raíz del programa"""
        for statement in node.statements:
            self.visit_statement(statement)

    def visit_statement(self, node):
        """Visita un statement y delega a la función apropiada"""
        if isinstance(node, FunctionDef):
            self.visit_function_def(node)
        elif isinstance(node, IfStmt):
            self.visit_if_statement(node)
        elif isinstance(node, AssignmentStmt):
            self.visit_assignment_stmt(node)
        elif isinstance(node, ReturnStmt):
            self.visit_return_stmt(node)
        # ... más casos para otros tipos de statements

    def visit_function_def(self, node):
        params = []
        for param in node.params:
            # Asegurarnos de que el tipo se mapee correctamente
            param_type = 'any'
            if param.type:
                param_type = self.type_mapping.get(param.type.name, 'any')
            params.append(f"{param.name}: {param_type}")
        
        return_type = self.type_mapping.get(node.return_type, 'any')
        
        self.emit(f"function {node.name}({', '.join(params)}): {return_type} {{")
        self.indentation += 1
        for stmt in node.body:
            self.visit_statement(stmt)
        self.indentation -= 1
        self.emit("}")

    def visit_assignment_stmt(self, node):
        value = self.visit_expression(node.value)
        self.emit(f"let {node.target.name} = {value};")

    def visit_return_stmt(self, node):
        if node.value:
            value = self.visit_expression(node.value)
            self.emit(f"return {value};")
        else:
            self.emit("return;")

    def visit_binary_expr(self, node):
        left = self.visit_expression(node.left)
        right = self.visit_expression(node.right)
        # Mapear operadores correctamente
        operator_map = {
            BinaryOp.PLUS: '+',
            BinaryOp.MINUS: '-',
            BinaryOp.MULTIPLY: '*',
            BinaryOp.DIVIDE: '/',
            BinaryOp.MODULO: '%',
            BinaryOp.EQUAL: '===',
            BinaryOp.NOT_EQUAL: '!==',
            BinaryOp.LESS: '<',
            BinaryOp.GREATER: '>',
            BinaryOp.LESS_EQUAL: '<=',
            BinaryOp.GREATER_EQUAL: '>='
        }
        operator = operator_map[node.operator]
        return f"{left} {operator} {right}"

    def visit_identifier(self, node):
        return node.name

    def visit_literal(self, node):
        return str(node.value)

    def transform_python_builtin(self, func_name: str, args: List[str]) -> str:
        """Transforma llamadas a funciones built-in de Python a TypeScript"""
        if func_name == 'print':
            return f"console.log({', '.join(args)})"
        elif func_name == 'len':
            return f"{args[0]}.length"
        elif func_name == 'str':
            return f"String({args[0]})"
        elif func_name == 'int':
            return f"parseInt({args[0]})"
        return f"{func_name}({', '.join(args)})"

    def visit_expression(self, node):
        """Visita y genera código para cualquier tipo de expresión"""
        if node is None:
            return ''
        
        # Manejar diferentes tipos de expresiones
        if isinstance(node, BinaryExpr):
            return self.visit_binary_expr(node)
        elif isinstance(node, UnaryExpr):
            return self.visit_unary_expr(node)
        elif isinstance(node, GroupingExpr):
            return self.visit_grouping_expr(node)
        elif isinstance(node, Literal):
            return self.visit_literal(node)
        elif isinstance(node, Identifier):
            return self.visit_identifier(node)
        elif isinstance(node, CallExpr):
            return self.visit_call_expr(node)
        else:
            raise ValueError(f"Tipo de expresión no soportado: {type(node)}")

    def visit_call_expr(self, node):
        """Genera código para llamadas a funciones"""
        func_name = node.callee.name
        # Mapear print de Python a console.log de TypeScript
        if func_name == 'print':
            func_name = 'console.log'
        
        args = [self.visit_expression(arg) for arg in node.arguments]
        return f"{func_name}({', '.join(args)})"

    def visit_unary_expr(self, node):
        """Genera código para expresiones unarias"""
        operator = '-' if node.operator == UnaryOp.NEGATE else '!'
        operand = self.visit_expression(node.operand)
        return f"{operator}{operand}"

    def visit_grouping_expr(self, node):
        """Genera código para expresiones agrupadas"""
        return f"({self.visit_expression(node.expression)})"