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
            
            # Si hay errores léxicos, detener el proceso
            if self.lexer.errors:
                for error in self.lexer.errors:
                    self.errors.append(error)
                return None
            
            # Realizar el análisis sintáctico
            result = self.parser.parse(lexer=self.lexer, debug=False)
            return result
        except Exception as e:
            # Eliminar este bloque de manejo de excepción genérica
            # ya que los errores sintácticos ya son manejados por p_error
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
        '''function_def : KEYWORD ID LPAREN parameter_list RPAREN type_annotation COLON NEWLINE INDENT statement_list DEDENT
                       | KEYWORD ID LPAREN RPAREN type_annotation COLON NEWLINE INDENT statement_list DEDENT'''
        if p[1] == 'def':
            name = p[2]
            params = [] if p[4] == ')' else p[4]
            return_type = p[5]
            body = p[10] if len(p) > 10 else p[9]
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
        func_name = p[1]
        
        # Verificar si la función existe
        if func_name not in self.known_functions and func_name not in self.user_defined_functions:
            # Buscar funciones similares para sugerir correcciones
            similar_functions = []
            for func in self.known_functions:
                # Mejorar la detección de similitud
                if abs(len(func) - len(func_name)) <= 2:  # Permitir hasta 2 caracteres de diferencia
                    # Verificar si las funciones son similares
                    common_chars = sum(1 for a, b in zip(func_name, func) if a == b)
                    if common_chars >= len(func_name) - 2:
                        similar_functions.append(func)
            
            suggestion = f"¿Quisiste decir '{similar_functions[0]}'?" if similar_functions else "Verifica el nombre de la función"
            error_msg = f"""Error sintáctico en línea {p.lineno}: Función '{func_name}' no definida
En el código:
    {self.source_lines[p.lineno - 1]}
    {' ' * self.source_lines[p.lineno - 1].find(func_name)}^ Aquí
Sugerencia: {suggestion}"""
            self.errors.append(error_msg)
        
        # Verificar argumentos
        if len(p) > 4 and p[3] is None:
            # Error en los argumentos, ya reportado
            p[0] = None
        else:
            if len(p) > 4:
                p[0] = CallExpr(Identifier(p[1]), p[3])
            else:
                p[0] = CallExpr(Identifier(p[1]), [])
    
    def p_arguments(self, p):
        '''arguments : expression
                     | arguments COMMA expression
                     | error COMMA
                     | arguments COMMA error'''
        if len(p) == 2:
            p[0] = [p[1]]
        elif len(p) == 4 and p[2] == ',' and p[3] == 'error':
            # Error: coma al final sin argumento
            func_name = self.source_lines[p.lineno - 1][:self.source_lines[p.lineno - 1].find('(')].strip()
            error_msg = f"""Error sintáctico en línea {p.lineno}: Argumento faltante después de la coma
En el código:
    {self.source_lines[p.lineno - 1]}
    {' ' * (self.source_lines[p.lineno - 1].rfind(','))}^ No se permite una coma al final sin un argumento
Sugerencia: Elimina la coma o agrega el argumento faltante
Ejemplo correcto: {func_name}(5) o {func_name}(5, 10)"""
            self.errors.append(error_msg)
            p[0] = None
        else:
            p[0] = p[1] + [p[3]]
    
    def p_type_annotation(self, p):
        '''type_annotation : ARROW ID
                          | empty'''
        if len(p) > 2:
            p[0] = Type(p[2])
        else:
            p[0] = None
    
    def p_empty(self, p):
        '''empty :'''
        pass
    
    def p_error(self, p):
        if p is None:
            error_msg = "Error sintáctico: Final inesperado del archivo"
            self.errors.append(error_msg)
            return
        
        # Obtener la línea completa donde está el error
        line = self.source_lines[p.lineno - 1]
        
        # Si la línea es un comentario, ignorarla
        if line.strip().startswith('#'):
            return
        
        column = p.lexpos - sum(len(l) + 1 for l in self.source_lines[:p.lineno - 1])

        # Detectar errores específicos de sintaxis
        if p.type == 'RPAREN' and ',' in line and line.strip().endswith(')'):
            # Detectar argumentos faltantes en llamadas a funciones
            func_name = line[:line.find('(')].strip()
            error_msg = f"""Error sintáctico en línea {p.lineno}: Argumento faltante en la llamada a la función '{func_name}'
En el código:
    {line}
    {' ' * (line.rfind(',') + 1)}^ Falta un argumento después de la coma
Ejemplo correcto: {line.replace(',)', ', 10)')}
Sugerencia: Las llamadas a funciones deben tener todos sus argumentos especificados"""
        elif p.type == 'STRING' or (p.type in ['LPAREN', 'RPAREN'] and '"' in line or "'" in line):
            # Verificar comillas no balanceadas
            quote_char = '"' if '"' in line else "'"
            if line.count(quote_char) % 2 != 0:
                # Construir el ejemplo correcto
                start_quote_pos = line.find(quote_char)
                unclosed_text = line[start_quote_pos + 1:]
                correct_example = f"{line[:start_quote_pos]}{quote_char}{unclosed_text}{quote_char})"
                
                error_msg = f"""Error sintáctico en línea {p.lineno}: Cadena de texto no cerrada correctamente
En el código:
    {line}
    {' ' * start_quote_pos}^ La cadena comienza aquí pero no se cierra correctamente
Sugerencia: Asegúrate de cerrar la cadena con {quote_char}
Ejemplo correcto: {correct_example}"""
        elif 'def' in line and ':' not in line:
            error_msg = f"""Error sintáctico en línea {p.lineno}: Falta el ':' después de la definición de función
En el código:
    {line}
    {' ' * len(line)}^ Falta el ':' aquí
Ejemplo correcto: {line}:"""
        else:
            # Mensaje genérico para otros errores sintácticos
            error_msg = f"""Error sintáctico en línea {p.lineno}: Token inesperado '{p.value}'
En el código:
    {line}
    {' ' * column}^ Aquí"""

        self.errors.append(error_msg)
        
        # Intentar recuperarse del error
        while True:
            tok = self.parser.token()
            if not tok or tok.type == 'NEWLINE':
                break
        self.parser.errok()