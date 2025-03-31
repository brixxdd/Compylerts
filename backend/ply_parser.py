import ply.yacc as yacc
from ply_lexer import PLYLexer, known_functions
from ast_nodes import (
    Program, ExpressionStmt, AssignmentStmt, ReturnStmt, FunctionDef, IfStmt,
    BinaryExpr, UnaryExpr, GroupingExpr, Literal, Identifier, CallExpr,
    Parameter, Type, BinaryOp, UnaryOp
)
import re
from symbol_table import SymbolTable, Symbol, Scope

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
        self.symbol_table = SymbolTable()
        self.semantic_errors = []
    
    def parse(self, text):
        """Analiza el texto y construye el AST"""
        self.source_lines = text.splitlines()
        self.errors = []
        self.semantic_errors = []
        self.symbol_table = SymbolTable()  # Reiniciar tabla de símbolos
        
        try:
            self.lexer = PLYLexer(text)
            
            # Verificar errores léxicos
            if self.lexer.errors:
                self.errors.extend(self.lexer.errors)
                return None
            
            # Realizar análisis sintáctico
            ast = self.parser.parse(lexer=self.lexer)
            
            # Verificar errores semánticos
            if self.semantic_errors:
                self.errors.extend(self.semantic_errors)
                return None
            
            return ast
        except Exception as e:
            self.errors.append(f"Error inesperado: {str(e)}")
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
        # Primero procesar todas las definiciones de funciones
        self.symbol_table = SymbolTable()  # Reiniciar tabla de símbolos
        
        # Primera pasada: registrar todas las funciones
        if p[1]:
            for stmt in p[1]:
                if isinstance(stmt, FunctionDef):
                    func_symbol = Symbol(
                        name=stmt.name,
                        type='function',
                        kind='function',
                        parameters=stmt.params,
                        return_type=stmt.return_type
                    )
                    self.symbol_table.define(func_symbol)
        
        # Segunda pasada: verificar el resto de las referencias
        if p[1]:
            for stmt in p[1]:
                if isinstance(stmt, CallExpr):
                    self._check_function_call(stmt, p.lineno)
                elif isinstance(stmt, Identifier):
                    self._check_variable_reference(stmt, p.lineno)
        
        p[0] = Program(p[1] if p[1] else [])
    
    def _check_function_call(self, call_expr, line):
        """Verifica una llamada a función"""
        func_name = call_expr.callee.name
        if not self.symbol_table.resolve(func_name) and func_name not in ['print', 'input', 'len']:
            self.semantic_errors.append(
                f"Error semántico en línea {line}: "
                f"Función '{func_name}' no está definida"
            )
    
    def _check_variable_reference(self, identifier, line):
        """Verifica una referencia a variable"""
        if not self.symbol_table.resolve(identifier.name):
            self.semantic_errors.append(
                f"Error semántico en línea {line}: "
                f"Variable '{identifier.name}' no está definida"
            )
    
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
        expr = p[1]
        
        # Verificar referencias a variables
        if isinstance(expr, CallExpr):
            # Verificar los argumentos de la llamada a función
            for arg in expr.arguments:
                if isinstance(arg, Identifier):
                    symbol = self.symbol_table.resolve(arg.name)
                    if not symbol and arg.name not in ['True', 'False', 'None']:
                        self.semantic_errors.append(
                            f"Error semántico en línea {p.lexer.lineno}: "  # Usar p.lexer.lineno
                            f"Variable '{arg.name}' no está definida"
                        )
        
        p[0] = ExpressionStmt(expr)
    
    def p_assignment_statement(self, p):
        '''assignment_statement : ID ASSIGN expression NEWLINE'''
        name = p[1]
        value = p[3]
        
        # Si estamos en el ámbito global, crear una variable global
        if self.symbol_table.current_scope == self.symbol_table.global_scope:
            symbol = Symbol(name=name, type='any', kind='variable')
            self.symbol_table.define(symbol)
        else:
            # Verificar si la variable existe en algún ámbito
            if not self.symbol_table.resolve(name):
                symbol = Symbol(name=name, type='any', kind='variable')
                self.symbol_table.define(symbol)
        
        p[0] = AssignmentStmt(Identifier(name), value)
    
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
        '''function_def : KEYWORD ID LPAREN parameter_list RPAREN type_annotation COLON NEWLINE INDENT statement_list DEDENT'''
        if p[1] == 'def':
            name = p[2]
            params = [] if p[4] == ')' else p[4]
            return_type = p[6].name if p[6] else 'None'
            
            # Crear nuevo ámbito para la función
            self.symbol_table.enter_scope("function")
            
            # Registrar los parámetros en el ámbito de la función
            for param in params:
                param_symbol = Symbol(
                    name=param.name,
                    type=param.type.name if param.type else 'any',
                    kind='parameter'
                )
                self.symbol_table.define(param_symbol)
            
            # Procesar el cuerpo de la función
                body = p[10]
            
            # Crear y registrar el símbolo de la función en el ámbito global
            func_symbol = Symbol(
                name=name,
                type='function',
                kind='function',
                parameters=params,
                return_type=return_type
            )
            
            # Salir del ámbito de la función
            self.symbol_table.exit_scope()
            
            # Registrar la función en el ámbito global
            if not self.symbol_table.define(func_symbol):
                self.semantic_errors.append(
                    f"Error semántico en línea {p.lineno()}: "
                    f"La función '{name}' ya está definida"
                )
                return
            
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
        if isinstance(p[1], (int, float)):
            p[0] = Literal(value=p[1], type_name='number')
        elif isinstance(p[1], str):
            if p[1] in ['True', 'False']:
                p[0] = Literal(value=p[1] == 'True', type_name='boolean')
        elif p[1] == 'None':
                p[0] = Literal(value=None, type_name='null')
        else:  # String normal
                p[0] = Literal(value=p[1], type_name='string')
    
    def p_group(self, p):
        '''group : LPAREN expression RPAREN'''
        p[0] = GroupingExpr(p[2])
    
    def p_call(self, p):
        '''call : ID LPAREN arguments RPAREN
                | ID LPAREN RPAREN'''
        func_name = p[1]
        args = [] if len(p) == 4 else p[3]
        
        # Verificar si la función existe y el número de argumentos
        symbol = self.symbol_table.resolve(func_name)
        if not symbol:
            if func_name not in ['print', 'input', 'len']:  # Funciones built-in
                self.semantic_errors.append(
                    f"Error semántico en línea {p.lexer.lineno}: "  # Usar p.lexer.lineno
                    f"Función '{func_name}' no está definida"
                )
            p[0] = CallExpr(Identifier(func_name), args)
            return
        
        if symbol.kind != 'function':
            self.semantic_errors.append(
                f"Error semántico en línea {p.lexer.lineno}: "  # Usar p.lexer.lineno
                f"'{func_name}' no es una función"
            )
            p[0] = CallExpr(Identifier(func_name), args)
            return
        
        expected_args = len(symbol.parameters) if symbol.parameters else 0
        received_args = len(args)
        if expected_args != received_args:
            self.semantic_errors.append(
                f"Error semántico en línea {p.lexer.lineno}: "  # Usar p.lexer.lineno
                f"La función '{func_name}' espera {expected_args} argumentos "
                f"pero recibió {received_args}"
            )
        
        p[0] = CallExpr(Identifier(func_name), args)
    
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
    {' ' * (self.source_lines[p.lineno - 1].rfind(',') + 1)}^ No se permite una coma al final sin un argumento
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