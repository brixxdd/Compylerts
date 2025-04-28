from ast_nodes import *
from typing import List, Dict
import re

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
            'list': 'Array<any>',
            'dict': 'Record<string, any>',
            'None': 'void',
            'any': 'any'
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
        elif isinstance(node, ForStmt):
            self.visit_for_stmt(node)
        elif isinstance(node, WhileStmt):
            self.visit_while_stmt(node)
        elif isinstance(node, AssignmentStmt):
            self.visit_assignment_stmt(node)
        elif isinstance(node, ReturnStmt):
            self.visit_return_stmt(node)
        elif isinstance(node, ExpressionStmt):
            self.visit_expression_stmt(node)
        # ... otros casos

    def visit_while_stmt(self, node):
        """Genera código para un bucle while"""
        condition = self.visit_expression(node.condition)
        self.emit(f"while ({condition}) {{")
        self.indentation += 1
        for stmt in node.body:
            self.visit_statement(stmt)
        self.indentation -= 1
        self.emit("}")

    def visit_expression_stmt(self, node):
        """Visita un expression statement y genera el código para la expresión"""
        expr_code = self.visit_expression(node.expression)
        self.emit(f"{expr_code};")

    def visit_function_def(self, node):
        params = []
        for param in node.params:
            # Asegurarnos de que el tipo se mapee correctamente
            param_type = 'any'
            if param.type:
                # El parser ya ha mapeado los tipos correctamente, usarlos directamente
                param_type = param.type.name
            params.append(f"{param.name}: {param_type}")
        
        # El parser ya ha mapeado el tipo de retorno, usar directamente
        return_type = node.return_type if node.return_type else 'void'
        
        self.emit(f"function {node.name}({', '.join(params)}): {return_type} {{")
        self.indentation += 1
        for stmt in node.body:
            self.visit_statement(stmt)
        self.indentation -= 1
        self.emit("}")

    def visit_assignment_stmt(self, node):
        """Genera código para asignaciones"""
        value = self.visit_expression(node.value)
        type_annotation = ''
        
        # Inferir tipo si es posible
        inferred_type = ''
        if isinstance(node.value, Literal):
            if node.value.type_name == 'number':
                inferred_type = 'number'
            elif node.value.type_name == 'string':
                inferred_type = 'string'
            elif node.value.type_name == 'boolean':
                inferred_type = 'boolean'
            elif node.value.type_name.startswith('list<'):
                # Extraer el tipo de los elementos de la lista
                element_type = node.value.type_name[5:-1]  # Remover 'list<' y '>'
                if '|' in element_type:
                    # Si es una lista con múltiples tipos
                    types = [self.type_mapping.get(t.strip(), 'any') for t in element_type.split('|')]
                    inferred_type = f"({' | '.join(types)})[]"
                else:
                    # Si es una lista de un solo tipo
                    mapped_type = self.type_mapping.get(element_type.strip(), 'any')
                    inferred_type = f"{mapped_type}[]"
            elif node.value.type_name == 'list':
                inferred_type = 'any[]'
        
        if hasattr(node, 'type') and node.type:
            type_annotation = f": {self.type_mapping.get(node.type.name, inferred_type or 'any')}"
        elif inferred_type:
            type_annotation = f": {inferred_type}"
        
        # Usar let para todas las asignaciones
        self.emit(f"let {node.target.name}{type_annotation} = {value};")

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
        """Genera código para literales"""
        if node.type_name.startswith('list<'):
            # Para listas, visitar cada elemento
            elements = [self.visit_expression(item) for item in node.value]
            return f"[{', '.join(elements)}]"
        elif node.type_name == 'string':
            # Asegurarse de que node.value sea un string
            if node.value is None:
                return '""'
            # Si el valor comienza con ` es un template string
            if isinstance(node.value, str):
                if node.value.startswith('`'):
                    return node.value  # Devolver el template string tal cual
                # Escapar las comillas dobles dentro del string
                escaped_value = node.value.replace('"', '\\"')
                return f'"{escaped_value}"'  # String normal
            return f'"{str(node.value)}"'
        elif node.type_name == 'number':
            return str(node.value)
        elif node.type_name == 'boolean':
            # Asegurar que el valor sea en minúscula para TypeScript
            if isinstance(node.value, str):
                return node.value.lower()
            return str(node.value).lower()
        elif node.type_name == 'null':
            return 'null'
        elif node.type_name == 'fstring':
            # Convertir f-strings de Python a template literals de TypeScript
            if isinstance(node.value, str):
                # Reemplazar {expr} con ${expr}
                ts_template = node.value.replace('{', '${')
                return f"`{ts_template}`"
            return f'`{str(node.value)}`'
        return str(node.value)

    def transform_python_builtin(self, func_name: str, args: List[str]) -> str:
        """Transforma llamadas a funciones built-in de Python a TypeScript"""
        def convert_to_template_string(arg: str) -> str:
            # Si el argumento es un string con {} para interpolación
            if arg.startswith('"') and arg.endswith('"') and '{' in arg and '}' in arg:
                # Quitar las comillas dobles
                content = arg[1:-1]
                # Convertir {expr} a ${expr}
                processed = re.sub(r'\{([^}]+)\}', r'${\1}', content)
                return f'`{processed}`'
            return arg

        # Procesar los argumentos para convertir strings con interpolación a template strings
        processed_args = [convert_to_template_string(arg) for arg in args]
        
        builtin_map = {
            'print': lambda args: f"console.log({', '.join(args)})",
            'len': lambda args: f"{args[0]}.length",
            'str': lambda args: f"String({args[0]})",
            'int': lambda args: f"parseInt({args[0]})",
            'float': lambda args: f"parseFloat({args[0]})",
            'list': lambda args: f"Array.from({args[0]})",
            'sum': lambda args: f"{args[0]}.reduce((a, b) => a + b, 0)",
            'max': lambda args: f"Math.max(...{args[0]})",
            'min': lambda args: f"Math.min(...{args[0]})"
        }
        
        if func_name in builtin_map:
            return builtin_map[func_name](processed_args)
        return f"{func_name}({', '.join(processed_args)})"

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
            # Convertir a string como último recurso
            try:
                return str(node)
            except:
                return f"/* Error: tipo de expresión no soportado: {type(node).__name__} */"

    def visit_call_expr(self, node):
        """Genera código para llamadas a funciones"""
        # Si el callee no es un Identifier, puede ser una expresión más compleja
        if not isinstance(node.callee, Identifier):
            # Intentar convertir la expresión a un string
            try:
                func_name = str(node.callee)
            except:
                func_name = "unknown_function"
            args = [self.visit_expression(arg) for arg in node.arguments]
            return f"{func_name}({', '.join(args)})"
            
        func_name = node.callee.name
        args = [self.visit_expression(arg) for arg in node.arguments]
        
        # Usar la transformación para funciones built-in
        if func_name in ['print', 'len', 'str', 'int', 'float', 'list', 'sum', 'max', 'min']:
            return self.transform_python_builtin(func_name, args)
        
        return f"{func_name}({', '.join(args)})"

    def visit_unary_expr(self, node):
        """Genera código para expresiones unarias"""
        operator = '-' if node.operator == UnaryOp.NEGATE else '!'
        operand = self.visit_expression(node.operand)
        return f"{operator}{operand}"

    def visit_grouping_expr(self, node):
        """Genera código para expresiones agrupadas"""
        return f"({self.visit_expression(node.expression)})"

    def visit_for_stmt(self, node):
        """Genera código para un bucle for"""
        variable_name = node.variable.name
        iterable = self.visit_expression(node.iterable)
        
        # Si el iterable es un rango, traducirlo a un bucle for numerado en TypeScript
        if isinstance(node.iterable, CallExpr) and isinstance(node.iterable.callee, Identifier) and node.iterable.callee.name == 'range':
            args = node.iterable.arguments
            if len(args) == 1:
                # range(end)
                self.emit(f"for (let {variable_name} = 0; {variable_name} < {self.visit_expression(args[0])}; {variable_name}++) {{")
            elif len(args) == 2:
                # range(start, end)
                self.emit(f"for (let {variable_name} = {self.visit_expression(args[0])}; {variable_name} < {self.visit_expression(args[1])}; {variable_name}++) {{")
            elif len(args) == 3:
                # range(start, end, step)
                step = self.visit_expression(args[2])
                step_comparison = "<" if not step.startswith("-") else ">"
                self.emit(f"for (let {variable_name} = {self.visit_expression(args[0])}; {variable_name} {step_comparison} {self.visit_expression(args[1])}; {variable_name} += {step}) {{")
        else:
            # Bucle for normal para otros iterables
            self.emit(f"for (const {variable_name} of {iterable}) {{")
        
        self.indentation += 1
        for stmt in node.body:
            self.visit_statement(stmt)
        self.indentation -= 1
        self.emit("}")

    def visit_if_statement(self, node):
        """Genera código para una sentencia if"""
        condition = self.visit_expression(node.condition)
        self.emit(f"if ({condition}) {{")
        self.indentation += 1
        
        # Visitar cada sentencia en el bloque then
        for stmt in node.then_branch:
            self.visit_statement(stmt)
        
        self.indentation -= 1
        
        # Manejar el bloque else si existe
        if node.else_branch:
            self.emit("} else {")
            self.indentation += 1
            
            for stmt in node.else_branch:
                self.visit_statement(stmt)
                
            self.indentation -= 1
        
        self.emit("}")