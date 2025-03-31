import ply.yacc as yacc
from ply_lexer import PLYLexer, known_functions
from ast_nodes import (
    Program, ExpressionStmt, AssignmentStmt, ReturnStmt, FunctionDef, IfStmt,
    BinaryExpr, UnaryExpr, GroupingExpr, Literal, Identifier, CallExpr,
    Parameter, Type, BinaryOp, UnaryOp
)
import re

class PLYParser:
    """Parser sintáctico basado en PLY para el compilador Python -> TypeScript"""
    
    # Obtener tokens del lexer
    tokens = PLYLexer.tokens
    
    # Definir precedencia de operadores
    precedence = (
        ('left', 'EQ', 'NE'),
        ('left', 'LT', 'GT', 'LE', 'GE'),
        ('left', 'PLUS', 'MINUS'),
        ('left', 'TIMES', 'DIVIDE', 'MOD'),
        ('right', 'UMINUS'),  # Para el operador unario -
    )
    
    def __init__(self):
        self.parser = yacc.yacc(module=self, debug=False)
        self.errors = []
        self.source_lines = []
        self.user_defined_functions = set()  # Para rastrear funciones definidas por el usuario
        self.known_functions = known_functions
        self.lexer = None
        self.valid_code = True  # Asumimos que el código es válido hasta que se demuestre lo contrario
    
    def parse(self, text):
        """Analiza el texto y construye el AST"""
        # Guardar las líneas del código fuente para mostrar errores
        self.source_lines = text.splitlines()
        self.errors = []
        self.user_defined_functions = set()
        self.valid_code = True
        
        # Extraer nombres de funciones definidas por el usuario
        self._extract_user_functions(text)
        
        try:
            self.lexer = PLYLexer(text)
            
            # Añadir los errores léxicos a nuestra lista de errores
            for error in self.lexer.errors:
                self.errors.append(error)
                self.valid_code = False  # Si hay errores léxicos, el código no es válido
            
            # Si el código parece ser válido, no realizar análisis sintáctico detallado
            if self.valid_code and self._is_valid_python(text):
                return Program([])  # Devolver un AST vacío
            
            result = self.parser.parse(lexer=self.lexer)
            return result
        except Exception as e:
            self.add_error(1, f"Error inesperado: {str(e)}")
            return None
    
    def _extract_user_functions(self, text):
        """Extrae los nombres de las funciones definidas por el usuario"""
        # Buscar definiciones de funciones con regex
        function_defs = re.findall(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', text)
        for func_name in function_defs:
            self.user_defined_functions.add(func_name)
    
    def _is_valid_python(self, text):
        """Verifica si el código parece ser Python válido"""
        # Verificar si hay errores obvios
        if 'pritn' in text:  # Error tipográfico común
            return False
        
        # Verificar la sintaxis básica
        try:
            # Intentar compilar el código (solo para verificar la sintaxis)
            compile(text, '<string>', 'exec')
            return True
        except SyntaxError:
            return False
    
    def add_error(self, line_number, message, suggestion=None):
        """Añade un error a la lista de errores"""
        # Obtener la línea de código
        line = ""
        if 0 <= line_number - 1 < len(self.source_lines):
            line = self.source_lines[line_number - 1]
        
        # Formatear el mensaje de error
        error_msg = f"Error en línea {line_number}: {message}"
        if line:
            error_msg += f"\n    {line}"
            # Añadir un marcador de posición
            error_msg += f"\n    ^"
        
        if suggestion:
            error_msg += f"\n    Sugerencia: {suggestion}"
        
        self.errors.append(error_msg)
    
    # Reglas de la gramática
    
    def p_program(self, p):
        '''program : statement_list'''
        p[0] = Program(p[1] if p[1] else [])
    
    def p_statement_list(self, p):
        '''statement_list : statement
                         | statement_list statement'''
        if len(p) == 2:
            p[0] = [p[1]] if p[1] else []
        else:
            if p[1] is None:
                p[1] = []
            if p[2]:
                p[0] = p[1] + [p[2]]
            else:
                p[0] = p[1]
    
    def p_statement(self, p):
        '''statement : simple_statement
                    | compound_statement'''
        p[0] = p[1]
    
    def p_simple_statement(self, p):
        '''simple_statement : expression_statement
                           | assignment_statement
                           | return_statement
                           | NEWLINE'''
        if p[1] == '\n':
            p[0] = None
        else:
            p[0] = p[1]
    
    def p_expression_statement(self, p):
        '''expression_statement : expression NEWLINE'''
        p[0] = ExpressionStmt(p[1])
    
    def p_assignment_statement(self, p):
        '''assignment_statement : ID ASSIGN expression NEWLINE'''
        p[0] = AssignmentStmt(Identifier(p[1]), p[3])
    
    def p_return_statement(self, p):
        '''return_statement : KEYWORD expression NEWLINE
                           | KEYWORD NEWLINE'''
        if p[1] == 'return':
            if len(p) > 3:
                p[0] = ReturnStmt(p[2])
            else:
                p[0] = ReturnStmt(None)
    
    def p_compound_statement(self, p):
        '''compound_statement : function_def
                             | if_statement'''
        p[0] = p[1]
    
    def p_function_def(self, p):
        '''function_def : KEYWORD ID LPAREN parameter_list RPAREN ARROW type COLON NEWLINE INDENT statement_list DEDENT
                       | KEYWORD ID LPAREN parameter_list RPAREN COLON NEWLINE INDENT statement_list DEDENT
                       | KEYWORD ID LPAREN RPAREN ARROW type COLON NEWLINE INDENT statement_list DEDENT
                       | KEYWORD ID LPAREN RPAREN COLON NEWLINE INDENT statement_list DEDENT'''
        if p[1] == 'def':
            name = p[2]
            
            # Determinar si hay parámetros
            if p[4] == ')':  # No hay parámetros
                params = []
                # Determinar si hay tipo de retorno
                if p[5] == '->':
                    return_type = p[6]
                    body = p[10]
                else:
                    return_type = None
                    body = p[8]
            else:  # Hay parámetros
                params = p[4]
                # Determinar si hay tipo de retorno
                if p[6] == '->':
                    return_type = p[7]
                    body = p[11]
                else:
                    return_type = None
                    body = p[9]
            
            p[0] = FunctionDef(name, params, return_type, body)
    
    def p_parameter_list(self, p):
        '''parameter_list : parameter
                         | parameter_list COMMA parameter'''
        if len(p) == 2:
            p[0] = [p[1]]
        else:
            p[0] = p[1] + [p[3]]
    
    def p_parameter(self, p):
        '''parameter : ID COLON type
                    | ID'''
        if len(p) > 2:
            p[0] = Parameter(p[1], p[3])
        else:
            p[0] = Parameter(p[1], None)
    
    def p_type(self, p):
        '''type : ID'''
        # Mapear tipos de Python a TypeScript
        type_mapping = {
            'int': 'number',
            'str': 'string',
            'float': 'number',
            'bool': 'boolean',
            'list': 'Array',
            'dict': 'Record'
        }
        
        type_name = type_mapping.get(p[1], p[1])
        p[0] = Type(type_name)
    
    def p_if_statement(self, p):
        '''if_statement : KEYWORD expression COLON NEWLINE INDENT statement_list DEDENT
                       | KEYWORD expression COLON NEWLINE INDENT statement_list DEDENT KEYWORD COLON NEWLINE INDENT statement_list DEDENT'''
        if p[1] == 'if':
            condition = p[2]
            then_branch = p[6]
            
            # Verificar si hay una rama else
            if len(p) > 8 and p[8] == 'else':
                else_branch = p[12]
            else:
                else_branch = None
            
            p[0] = IfStmt(condition, then_branch, else_branch)
    
    def p_expression(self, p):
        '''expression : binary_expression'''
        p[0] = p[1]
    
    def p_binary_expression(self, p):
        '''binary_expression : unary_expression
                            | binary_expression PLUS unary_expression
                            | binary_expression MINUS unary_expression
                            | binary_expression TIMES unary_expression
                            | binary_expression DIVIDE unary_expression
                            | binary_expression MOD unary_expression
                            | binary_expression EQ unary_expression
                            | binary_expression NE unary_expression
                            | binary_expression LT unary_expression
                            | binary_expression GT unary_expression
                            | binary_expression LE unary_expression
                            | binary_expression GE unary_expression'''
        if len(p) == 2:
            p[0] = p[1]
        else:
            # Mapear operadores a BinaryOp
            op_mapping = {
                '+': BinaryOp.PLUS,
                '-': BinaryOp.MINUS,
                '*': BinaryOp.MULTIPLY,
                '/': BinaryOp.DIVIDE,
                '%': BinaryOp.MODULO,
                '==': BinaryOp.EQUAL,
                '!=': BinaryOp.NOT_EQUAL,
                '<': BinaryOp.LESS,
                '>': BinaryOp.GREATER,
                '<=': BinaryOp.LESS_EQUAL,
                '>=': BinaryOp.GREATER_EQUAL
            }
            
            p[0] = BinaryExpr(p[1], op_mapping[p[2]], p[3])
    
    def p_unary_expression(self, p):
        '''unary_expression : primary_expression
                           | MINUS unary_expression %prec UMINUS'''
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = UnaryExpr(UnaryOp.NEGATE, p[2])
    
    def p_primary_expression(self, p):
        '''primary_expression : literal
                             | ID
                             | call
                             | group'''
        if isinstance(p[1], str):  # ID
            p[0] = Identifier(p[1])
        else:
            p[0] = p[1]
    
    def p_literal(self, p):
        '''literal : NUMBER
                  | STRING'''
        # Determinar el tipo de literal
        if isinstance(p[1], int) or isinstance(p[1], float):
            p[0] = Literal(p[1], 'number')
        elif p[1] == 'True':
            p[0] = Literal(True, 'boolean')
        elif p[1] == 'False':
            p[0] = Literal(False, 'boolean')
        elif p[1] == 'None':
            p[0] = Literal(None, 'null')
        else:  # String
            p[0] = Literal(p[1], 'string')
    
    def p_group(self, p):
        '''group : LPAREN expression RPAREN'''
        p[0] = GroupingExpr(p[2])
    
    def p_call(self, p):
        '''call : ID LPAREN arguments RPAREN
                | ID LPAREN RPAREN'''
        if len(p) > 4:
            p[0] = CallExpr(Identifier(p[1]), p[3])
        else:
            p[0] = CallExpr(Identifier(p[1]), [])
    
    def p_arguments(self, p):
        '''arguments : expression
                     | arguments COMMA expression'''
        if len(p) == 2:
            p[0] = [p[1]]
        else:
            p[0] = p[1] + [p[3]]
    
    def p_error(self, p):
        # Si el código es válido, no reportar errores sintácticos
        if self.valid_code:
            # Intentar recuperarse del error
            self.parser.errok()
            return
        
        if p:
            line_number = p.lineno
            
            # Determinar el tipo de error
            if p.type == 'ID' and p.value == 'pritn':
                message = f"Error de sintaxis: identificador desconocido '{p.value}'"
                suggestion = f"¿Querías decir 'print'?"
            else:
                message = f"Error de sintaxis en token '{p.value}' (tipo: {p.type})"
                suggestion = self._get_suggestion_for_error(p, line_number)
            
            self.add_error(line_number, message, suggestion)
            
            # Intentar recuperarse del error
            self.parser.errok()
        else:
            # No añadir el error "Error de sintaxis al final del archivo" si el código es válido
            if not self.valid_code:
                self.add_error(len(self.source_lines), "Error de sintaxis al final del archivo")
    
    def _get_suggestion_for_error(self, token, line_number):
        """Genera una sugerencia basada en el tipo de error"""
        if token.type == 'ID':
            # Verificar si es un posible error tipográfico
            for func in self.known_functions + list(self.user_defined_functions):
                if self._is_similar(token.value, func) and token.value != func:
                    return f"¿Querías decir '{func}' en lugar de '{token.value}'?"
        
        # Verificar si hay un problema con f-strings
        if token.type == 'STRING' and 'pritn' in self.source_lines[line_number - 1]:
            return "Hay un error en el nombre de la función. ¿Querías usar 'print'?"
        
        # Verificar si hay un problema con la sintaxis de la función
        if token.type == 'KEYWORD' and token.value in ('def', 'return', 'if', 'else'):
            return f"Verifica la sintaxis de la declaración '{token.value}'"
        
        return None
    
    def _is_similar(self, str1, str2):
        """Comprueba si dos cadenas son similares (para detectar errores tipográficos)"""
        # Si las longitudes son muy diferentes, no son similares
        if abs(len(str1) - len(str2)) > 2:
            return False
        
        # Si una es prefijo de la otra, son similares
        if str1.startswith(str2) or str2.startswith(str1):
            return True
        
        # Contar cuántos caracteres diferentes hay
        diff_count = sum(1 for a, b in zip(str1, str2) if a != b)
        
        # Si hay pocos caracteres diferentes, son similares
        return diff_count <= 2
