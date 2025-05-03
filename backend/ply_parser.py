import ply.yacc as yacc
from ply_lexer import PLYLexer, known_functions
from ast_nodes import (
    Program, ExpressionStmt, AssignmentStmt, ReturnStmt, FunctionDef, IfStmt,
    BinaryExpr, UnaryExpr, GroupingExpr, Literal, Identifier, CallExpr,
    Parameter, Type, BinaryOp, UnaryOp, ForStmt, WhileStmt
)
import re
from symbol_table import SymbolTable, Symbol, Scope
from error_handler import error_handler, CompilerError, ErrorType

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
    
    def __init__(self, source_code: str):
        """Inicializa el parser"""
        self.source_code = source_code
        self.source_lines = source_code.splitlines()
        self.valid_code = True
        self.user_defined_functions = set()
        self.known_functions = ['print', 'input', 'len', 'str', 'int', 'float', 'list', 'range']
        self.function_contexts = []
        self.indent_level = 0
        self.parser = yacc.yacc(module=self)
        self.symbol_table = SymbolTable()
        self.semantic_errors = []
        self.current_scope = None
    
    # ======================================================================
    # REGLAS BNF PARA EL LENGUAJE
    # ======================================================================

    # <program> ::= <statement_list>
    def p_program(self, p):
        '''program : statement_list'''
        # Guardar las funciones pre-registradas
        pre_registered_functions = set(self.user_defined_functions)
        known_functions = list(self.known_functions)
        
        # Reiniciar tabla de símbolos pero mantener las funciones pre-registradas
        self.symbol_table = SymbolTable()
        
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
                    # Añadir a funciones conocidas si no estaba ya
                    if stmt.name not in pre_registered_functions:
                        self.user_defined_functions.add(stmt.name)
                    if stmt.name not in known_functions:
                        self.known_functions.append(stmt.name)
        
        # Segunda pasada: verificar el resto de las referencias
        if p[1]:
            for stmt in p[1]:
                if isinstance(stmt, CallExpr):
                    self._check_function_call(stmt, p.lineno(0) if hasattr(p, 'lineno') else 0)
                elif isinstance(stmt, Identifier):
                    self._check_variable_reference(stmt, p.lineno(0) if hasattr(p, 'lineno') else 0)
        
        p[0] = Program(p[1] if p[1] else [])
    
    # <statement_list> ::= <statement> | <statement_list> <statement>
    def p_statement_list(self, p):
        '''statement_list : statement
                         | statement_list statement'''
        if len(p) == 2:
            p[0] = [p[1]] if p[1] else []
        else:
            # Asegurarse de que p[1] sea una lista, no None
            if p[1] is None:
                p[1] = []
            # Asegurarse de que p[2] sea una sentencia válida
            if p[2]:
                p[0] = p[1] + [p[2]]
            else:
                p[0] = p[1]
    
    # <statement> ::= <simple_statement> | <compound_statement>
    def p_statement(self, p):
        '''statement : simple_statement
                    | compound_statement'''
        p[0] = p[1]
    
    # <simple_statement> ::= <expression_statement> | <assignment_statement> | <return_statement> | NEWLINE
    def p_simple_statement(self, p):
        '''simple_statement : expression_statement
                           | assignment_statement
                           | return_statement
                           | NEWLINE'''
        # Manejar caso de línea en blanco
        if len(p) > 1 and p[1] == '\n':
            p[0] = None
        else:
            p[0] = p[1]
    
    # <expression_statement> ::= <expression> NEWLINE | ID LPAREN <arguments> RPAREN NEWLINE
    def p_expression_statement(self, p):
        '''expression_statement : expression NEWLINE
                              | call NEWLINE
                              | ID LPAREN arguments RPAREN NEWLINE
                              | ID LPAREN RPAREN NEWLINE'''
        if len(p) >= 5 and p[1] != 'if' and p[1] != 'for' and p[1] != 'while':
            # Es una llamada a función directa (ID LPAREN args RPAREN)
            func_name = p[1]
            args = [] if p[3] == ')' else p[3]
            
            # Verificar si la función existe
            if func_name not in self.user_defined_functions and func_name not in self.known_functions:
                error_handler.add_error(CompilerError(
                    type=ErrorType.SEMANTIC,
                    line=p.lineno(1),
                    message=f"Función '{func_name}' no está definida",
                    code_line=self.source_lines[p.lineno(1) - 1],
                    column=self.find_column(p),
                    suggestion=f"Asegúrate de que la función '{func_name}' esté definida antes de usarla"
                ))
                self.valid_code = False
            
            expr = CallExpr(Identifier(func_name), args)
            p[0] = ExpressionStmt(expr)
        else:
            # Es una expresión normal
            expr = p[1]
            p[0] = ExpressionStmt(expr)
    
    # <assignment_statement> ::= ID ASSIGN <expression> NEWLINE
    def p_assignment_statement(self, p):
        '''assignment_statement : ID ASSIGN expression NEWLINE
                               | ID ASSIGN list_literal NEWLINE'''
        name = p[1]
        value = p[3]
        
        # Crear variable en la tabla de símbolos
        # Detectar tipo según el valor si es posible
        var_type = 'any'
        if isinstance(value, Literal):
            var_type = value.type_name
        
        symbol = Symbol(name=name, type=var_type, kind='variable')
        self.symbol_table.define(symbol)
        
        p[0] = AssignmentStmt(Identifier(name), value)
    
    # <return_statement> ::= KEYWORD <expression> NEWLINE | KEYWORD NEWLINE
    def p_return_statement(self, p):
        '''return_statement : KEYWORD expression NEWLINE
                           | KEYWORD NEWLINE'''
        if p[1] == 'return':
            # Verificar si estamos en contexto de función
            # Para esta versión simplificada, asumiremos que cualquier return con indentación
            # está dentro de una función
            is_in_function = self.indent_level > 0
            
            for symbol in getattr(self.symbol_table, 'symbols', []):
                if getattr(symbol, 'kind', None) == 'function':
                    is_in_function = True
                    break
            
            # Añadir verificación para comprobar si estamos dentro de una definición de función
            if not is_in_function:
                if hasattr(p, 'lexer') and hasattr(p.lexer, 'last_tokens'):
                    for token in p.lexer.last_tokens:
                        if token.type == 'KEYWORD' and token.value == 'def':
                            is_in_function = True
                            break
            
            if not is_in_function:
                lineno = p.lineno(1) if hasattr(p, 'lineno') else 0
                line = self.source_lines[lineno - 1] if lineno <= len(self.source_lines) else ""
                column = self.find_column(p)
                error_handler.add_error(CompilerError(
                    type=ErrorType.SEMANTIC,
                    line=lineno,
                    message="La sentencia 'return' debe estar dentro de una función",
                    code_line=line,
                    column=column,
                    suggestion="Asegúrate de que la sentencia 'return' esté dentro de la definición de una función."
                ))
                p[0] = None
                return
            
            if len(p) > 3:
                p[0] = ReturnStmt(p[2])
            else:
                p[0] = ReturnStmt(None)
    
    # <compound_statement> ::= <function_def> | <if_statement> | <for_statement> | <while_statement>
    def p_compound_statement(self, p):
        '''compound_statement : function_def
                             | if_statement
                             | for_statement
                             | while_statement'''
        p[0] = p[1]

    


    # <function_def> ::= KEYWORD ID LPAREN <parameter_list> RPAREN <return_type> COLON NEWLINE INDENT <statement_list> DEDENT
    def p_function_def(self, p):
        '''function_def : KEYWORD ID LPAREN parameter_list RPAREN return_type COLON NEWLINE INDENT statement_list DEDENT'''
        if p[1] == 'def':
            name = p[2]
            params = p[4] if p[4] else []
            # Mapear el tipo de retorno
            type_mapping = {
                'int': 'number',
                'str': 'string',
                'float': 'number',
                'bool': 'boolean',
                'list': 'Array',
                'dict': 'Record',
                'None': 'void'
            }
            return_type = p[6].name if p[6] else 'void'
            return_type = type_mapping.get(return_type, return_type)
            body = p[10]
            
            # Registrar la función en la tabla de símbolos
            func_symbol = Symbol(
                name=name,
                type='function',
                kind='function',
                parameters=params,
                return_type=return_type
            )
            self.symbol_table.define(func_symbol)
            # Añadir la función a los símbolos conocidos
            self.user_defined_functions.add(name)
            self.known_functions.append(name)
            
            # Marcar que estamos en un contexto de función para reconocer returns
            self.indent_level = 4
            
            p[0] = FunctionDef(name, params, return_type, body)
            
    # Error: Falta ":" después del tipo de retorno en la definición de función
    def p_function_def_missing_colon(self, p):
        '''function_def : KEYWORD ID LPAREN parameter_list RPAREN return_type NEWLINE INDENT statement_list DEDENT'''
        if p[1] == 'def':
            line = p.lineno(1) if hasattr(p, 'lineno') else 0
            if line > 0 and line <= len(self.source_lines):
                code_line = self.source_lines[line - 1]
                # Buscar dónde debería ir el ":"
                if '->' in code_line:
                    # El ":" debería ir después del tipo de retorno
                    colon_pos = code_line.rfind('>') + 1
                else:
                    # El ":" debería ir después del paréntesis de cierre
                    colon_pos = code_line.rfind(')')
                    if colon_pos == -1:
                        colon_pos = len(code_line)
                    else:
                        colon_pos += 1
                
                error_handler.add_error(CompilerError(
                    type=ErrorType.SYNTACTIC,
                    line=line,
                    message="Falta el carácter ':' en la definición de función",
                    code_line=code_line,
                    column=colon_pos,
                    suggestion="Añade ':' después del tipo de retorno o paréntesis de cierre"
                ))
                self.valid_code = False
            
            # Intentar recuperarse del error
            name = p[2]
            params = p[4] if p[4] else []
            return_type = p[6].name if p[6] else 'void'
            body = p[9] if p[9] else []
            
            p[0] = FunctionDef(name, params, return_type, body)
    
    # <parameter_list> ::= <parameter> | <parameter_list> COMMA <parameter>
    def p_parameter_list(self, p):
        '''parameter_list : parameter
                         | parameter_list COMMA parameter'''
        if len(p) == 2:
            p[0] = [p[1]]
        else:
            p[0] = p[1] + [p[3]]
    
    def p_parameter(self, p):
        '''parameter : ID COLON ID
                    | ID'''
        if len(p) == 4:
            # Mapear tipos de Python a TypeScript
            type_mapping = {
                'int': 'number',
                'str': 'string',
                'float': 'number',
                'bool': 'boolean',
                'list': 'Array',
                'dict': 'Record'
            }
            type_name = type_mapping.get(p[3], p[3])
            p[0] = Parameter(p[1], Type(type_name))
        else:
            p[0] = Parameter(p[1], None)
    
    # <type> ::= ID
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
    
    # <if_statement> ::= KEYWORD expression COLON NEWLINE INDENT statement_list_with_calls DEDENT
    #                  | KEYWORD expression COLON NEWLINE INDENT statement_list_with_calls DEDENT KEYWORD COLON NEWLINE INDENT statement_list_with_calls DEDENT
    def p_if_statement(self, p):
        '''if_statement : KEYWORD expression COLON NEWLINE INDENT statement_list DEDENT
                       | KEYWORD expression COLON NEWLINE INDENT statement_list DEDENT KEYWORD COLON NEWLINE INDENT statement_list DEDENT'''
        if p[1] == 'if':
            condition = p[2]
            then_branch = p[6] if p[6] else []
            else_branch = None
            if len(p) > 8:
                if p[8] == 'else':
                    else_branch = p[12] if p[12] else []
                else:
                    self.semantic_errors.append(f"Error de sintaxis en línea {p.lineno(8)}: se esperaba 'else', se encontró '{p[8]}'")
                    p[0] = None
                    return
            
            # Verificar y procesar sentencias en los bloques
            for stmt in then_branch:
                if hasattr(stmt, 'expression') and isinstance(stmt.expression, CallExpr):
                    pass
            
            if else_branch:
                for stmt in else_branch:
                    if hasattr(stmt, 'expression') and isinstance(stmt.expression, CallExpr):
                        pass
            
            # Crear un WRAPPER para toda la sentencia
            # Este enfoque nos permite continuar incluso si hay errores en los bloques individuales
            p[0] = IfStmt(condition, then_branch, else_branch)
            # Omitir errores específicos relacionados con print dentro de bloques
            error_indices = []
            for i, error in enumerate(self.semantic_errors):
                if "Token inesperado 'print'" in error:
                    error_indices.append(i)
            
            # Eliminar errores desde el final para no afectar los índices
            for i in sorted(error_indices, reverse=True):
                if i < len(self.semantic_errors):
                    self.semantic_errors.pop(i)
        else:
            self.semantic_errors.append(f"Error de sintaxis en línea {p.lineno(1)}: se esperaba 'if', se encontró '{p[1]}'")
            p[0] = None
    
    # <for_statement> ::= KEYWORD ID KEYWORD expression COLON NEWLINE INDENT <statement_list> DEDENT
    def p_for_statement(self, p):
        '''for_statement : KEYWORD ID KEYWORD expression COLON NEWLINE INDENT statement_list DEDENT'''
        if p[1] == 'for' and p[3] == 'in':
            variable = Identifier(p[2])
            iterable = p[4]
            body = p[8] if p[8] else []
            
            # Registrar la variable del bucle en la tabla de símbolos
            symbol = Symbol(name=p[2], type='any', kind='variable')
            self.symbol_table.define(symbol)
            
            # Verificar y procesar sentencias en el cuerpo
            for stmt in body:
                if hasattr(stmt, 'expression') and isinstance(stmt.expression, CallExpr):
                    pass
            
            p[0] = ForStmt(variable, iterable, body)
            
            # Omitir errores específicos relacionados con print dentro de bloques
            error_indices = []
            for i, error in enumerate(self.semantic_errors):
                if "Token inesperado 'print'" in error:
                    error_indices.append(i)
            
            # Eliminar errores desde el final para no afectar los índices
            for i in sorted(error_indices, reverse=True):
                if i < len(self.semantic_errors):
                    self.semantic_errors.pop(i)
        else:
            error_token = p[3] if p[1] == 'for' else p[1]
            expected = 'in' if p[1] == 'for' else 'for'
            self.semantic_errors.append(f"Error de sintaxis en línea {p.lineno(1)}: se esperaba '{expected}', se encontró '{error_token}'")
            p[0] = None

    # <while_statement> ::= KEYWORD expression COLON NEWLINE INDENT statement_list DEDENT
    def p_while_statement(self, p):
        '''while_statement : KEYWORD expression COLON NEWLINE INDENT statement_list DEDENT'''
        if p[1] == 'while':
            condition = p[2]
            body = p[6] if p[6] else []
            
            # Verificar y procesar sentencias en el cuerpo
            for stmt in body:
                if hasattr(stmt, 'expression') and isinstance(stmt.expression, CallExpr):
                    pass
            
            p[0] = WhileStmt(condition, body)
            
            # Omitir errores específicos relacionados con print dentro de bloques
            error_indices = []
            for i, error in enumerate(self.semantic_errors):
                if "Token inesperado 'print'" in error:
                    error_indices.append(i)
            
            # Eliminar errores desde el final para no afectar los índices
            for i in sorted(error_indices, reverse=True):
                if i < len(self.semantic_errors):
                    self.semantic_errors.pop(i)
        else:
            self.semantic_errors.append(f"Error de sintaxis en línea {p.lineno(1)}: se esperaba 'while', se encontró '{p[1]}'")
            p[0] = None

    
    # <expression> ::= STRING | NUMBER | ID | ...
    def p_expression_string(self, p):
        '''expression : STRING'''
        p[0] = Literal(value=p[1], type_name='string')

    # <expression> ::= <binary_expression> | <primary_expression> | NUMBER | <list_literal> | FSTRING
    def p_expression(self, p):
        '''expression : binary_expression
                     | primary_expression
                     | NUMBER
                     | list_literal
                     | FSTRING'''
        if isinstance(p[1], (int, float)):
            p[0] = Literal(value=p[1], type_name='number')
        elif isinstance(p[1], str) and p[1].startswith('f'):
            # Es una f-string, extraer el contenido
            content = p[1][2:-1]  # Remover f" y "
            p[0] = Literal(value=content, type_name='fstring')
        else:
            p[0] = p[1]
    
    # <binary_expression> ::= <unary_expression> | <binary_expression> PLUS <unary_expression> | ...
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
    
    # <unary_expression> ::= <primary_expression> | MINUS <unary_expression> %prec UMINUS
    def p_unary_expression(self, p):
        '''unary_expression : primary_expression
                           | MINUS unary_expression %prec UMINUS'''
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = UnaryExpr(UnaryOp.NEGATE, p[2])
    
    # <primary_expression> ::= <literal> | ID | <call> | <group> | <list_literal>
    def p_primary_expression(self, p):
        '''primary_expression : literal
                             | ID
                             | call
                             | group
                             | list_literal'''
        if len(p) == 2 and isinstance(p[1], str):  # ID
            # Verificar si el identificador está definido
            if p[1] not in self.user_defined_functions and p[1] not in self.known_functions and p[1] not in ['True', 'False', 'None']:
                error_handler.add_error(CompilerError(
                    type=ErrorType.SEMANTIC,
                    line=p.lineno(1),
                    message=f"Identificador '{p[1]}' no está definido",
                    code_line=self.source_lines[p.lineno(1) - 1],
                    column=self.find_column(p),
                    suggestion=f"Asegúrate de definir '{p[1]}' antes de usarlo"
                ))
                self.valid_code = False
            p[0] = Identifier(p[1])
        else:
            p[0] = p[1]
    
    # <literal> ::= NUMBER | STRING
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
            else:
                # Aquí ya no necesitamos verificación especial para f-strings
                # ya que se tratan como strings normales
                p[0] = Literal(value=p[1], type_name='string')
    
    # <group> ::= LPAREN <expression> RPAREN
    def p_group(self, p):
        '''group : LPAREN expression RPAREN'''
        p[0] = GroupingExpr(p[2])
    
    # <call> ::= ID LPAREN <arguments> RPAREN | ID LPAREN RPAREN
    def p_call(self, p):
        '''call : ID LPAREN arguments RPAREN
                | ID LPAREN RPAREN'''
        func_name = p[1]
        args = [] if len(p) == 4 else p[3]
        
        # Verificar posibles errores de argumentos
        if hasattr(p, 'lexer') and hasattr(p.lexer, 'last_tokens') and len(p.lexer.last_tokens) >= 2:
            # Buscar patrón de tokens que indique coma suelta
            last_tokens = p.lexer.last_tokens[-2:]
            if any(t.type == 'COMMA' and p.lexer.last_tokens[-1].type == 'RPAREN' for t in last_tokens):
                lineno = p.lineno(1) if hasattr(p, 'lineno') else 0
                if lineno > 0 and lineno <= len(self.source_lines):
                    line = self.source_lines[lineno - 1]
                    comma_pos = line.rfind(',', 0, line.rfind(')'))
                    if comma_pos != -1:
                        error_handler.add_error(CompilerError(
                            type=ErrorType.SYNTACTIC,
                            line=lineno,
                            message=f"Coma suelta en la llamada a función '{func_name}'",
                            code_line=line,
                            column=comma_pos,
                            suggestion="Elimina la coma o añade otro argumento después de la coma"
                        ))
                        self.valid_code = False
        
        # Manejo especial para funciones built-in como print
        if func_name in ['print', 'input', 'len']:
            p[0] = CallExpr(Identifier(func_name), args)
            return
        
        # Verificar si la función existe
        if func_name not in self.user_defined_functions and func_name not in self.known_functions:
            error_handler.add_error(CompilerError(
                type=ErrorType.SEMANTIC,
                line=p.lineno(1),
                message=f"Función '{func_name}' no está definida",
                code_line=self.source_lines[p.lineno(1) - 1],
                column=self.find_column(p),
                suggestion=f"Asegúrate de que la función '{func_name}' esté definida antes de usarla"
            ))
            self.valid_code = False
        
        # Verificar argumentos
        for arg in args:
            if isinstance(arg, Identifier):
                if not hasattr(self, 'variables'):
                    # Crear el atributo si no existe
                    self.variables = set()
                
                if arg.name not in self.variables and arg.name not in ['True', 'False', 'None']:
                    error_handler.add_error(CompilerError(
                        type=ErrorType.SEMANTIC,
                        line=p.lineno(1),
                        message=f"Variable '{arg.name}' no está definida",
                        code_line=self.source_lines[p.lineno(1) - 1],
                        column=self.find_column(p),
                        suggestion=f"Asegúrate de definir la variable '{arg.name}' antes de usarla"
                    ))
                    self.valid_code = False
        
        p[0] = CallExpr(Identifier(func_name), args)
    
    # <arguments> ::= <expression> | <arguments> COMMA <expression>
    def p_arguments(self, p):
        '''arguments : expression
                     | arguments COMMA expression
                     | STRING
                     | arguments COMMA STRING'''
        if len(p) == 2:
            # Si es un string literal, crear un objeto Literal
            if isinstance(p[1], str):
                p[0] = [Literal(value=p[1], type_name='string')]
            else:
                p[0] = [p[1]]
        else:
            # Si es un string literal, crear un objeto Literal
            value = p[3]
            if isinstance(value, str):
                value = Literal(value=value, type_name='string')
            p[0] = p[1] + [value]
    
    # Nueva regla para detectar comas sueltas en argumentos
    def p_arguments_trailing_comma(self, p):
        '''arguments : arguments COMMA'''
        # Se detectó una coma suelta al final de la lista de argumentos
        line = p.lineno(2) if hasattr(p, 'lineno') else 0
        if line > 0 and line <= len(self.source_lines):
            code_line = self.source_lines[line - 1]
            # Encontrar la posición de la coma
            comma_pos = code_line.rfind(',')
            
            # En caso de que existan comas consecutivas, buscar la coma específica
            # que está causando el error (la que está justo antes del paréntesis de cierre)
            closing_paren_pos = code_line.find(')', comma_pos)
            if closing_paren_pos != -1:
                # Verificar si no hay nada significativo entre la coma y el paréntesis
                between_text = code_line[comma_pos+1:closing_paren_pos].strip()
                if not between_text:  # Si está vacío, es una coma suelta
                    error_handler.add_error(CompilerError(
                        type=ErrorType.SYNTACTIC,
                        line=line,
                        message="Coma suelta en argumentos de función",
                        code_line=code_line,
                        column=comma_pos,
                        suggestion="Elimina la coma o añade otro argumento después de la coma"
                    ))
                    self.valid_code = False
            
        # Devolver los argumentos que ya teníamos antes de la coma
        p[0] = p[1]
    
    # <return_type> ::= ARROW TYPE | empty
    def p_return_type(self, p):
        '''return_type : ARROW ID
                          | empty'''
        if len(p) > 2:
            p[0] = Type(p[2])
        else:
            p[0] = None
    
    # <empty> ::=
    def p_empty(self, p):
        '''empty :'''
        pass
    
    # <list_literal> ::= LBRACKET <list_items> RBRACKET | LBRACKET RBRACKET
    def p_list_literal(self, p):
        '''list_literal : LBRACKET list_items RBRACKET'''
        items = p[2] if p[2] else []
        # Determinar el tipo de los elementos
        element_types = set()
        for item in items:
            if isinstance(item, Literal):
                element_types.add(item.type_name)
        
        # Si todos los elementos son del mismo tipo, usar ese tipo
        if len(element_types) == 1:
            list_type = f"list<{next(iter(element_types))}>"
        else:
            # Si hay múltiples tipos, indicarlos en el tipo de la lista
            list_type = f"list<{' | '.join(element_types)}>" if element_types else "list"
        
        p[0] = Literal(value=items, type_name=list_type)

    # <list_items> ::= <expression> | <list_items> COMMA <expression>
    def p_list_items(self, p):
        '''list_items : expression
                      | list_items COMMA expression
                      | empty'''
        if len(p) == 2:
            if p[1] is None:  # empty
                p[0] = []
            else:
                p[0] = [p[1]]
        elif len(p) == 4:
            p[0] = p[1] + [p[3]]

    # Manejo de errores
    def p_error(self, p):
        if p is None:
            # Error al final del archivo
            error_handler.add_error(CompilerError(
                type=ErrorType.SYNTACTIC,
                line=len(self.source_lines),
                message="Error de sintaxis al final del archivo",
                code_line=self.source_lines[-1] if self.source_lines else "",
                column=len(self.source_lines[-1]) if self.source_lines else 0,
                suggestion="Verifica que no falte código o que esté correctamente terminado"
            ))
        else:
            line = self.source_lines[p.lineno - 1]
            error_handler.add_error(CompilerError(
                type=ErrorType.SYNTACTIC,
                line=p.lineno,
                message=f"Error de sintaxis cerca de '{p.value}'",
                code_line=line,
                column=self.find_column(p),
                suggestion="Revisa la sintaxis del código en esta línea"
            ))
        self.valid_code = False

    def check_undefined_function(self, func_name: str, lineno: int):
        """Verifica si una función está definida"""
        if func_name not in self.user_defined_functions and func_name not in self.known_functions:
            line = self.source_lines[lineno - 1]
            error_handler.add_error(CompilerError(
                type=ErrorType.SEMANTIC,
                line=lineno,
                message=f"Función '{func_name}' no está definida",
                code_line=line,
                column=line.find(func_name),
                suggestion=f"Asegúrate de que la función '{func_name}' esté definida antes de usarla"
            ))
            self.valid_code = False

    def check_undefined_variable(self, var_name: str, lineno: int):
        """Verifica si una variable está definida"""
        if var_name not in self.variables:
            line = self.source_lines[lineno - 1]
            error_handler.add_error(CompilerError(
                type=ErrorType.SEMANTIC,
                line=lineno,
                message=f"Variable '{var_name}' no está definida",
                code_line=line,
                column=line.find(var_name),
                suggestion=f"Asegúrate de definir la variable '{var_name}' antes de usarla"
            ))
            self.valid_code = False

    def find_column(self, token):
        """Encuentra la columna de un token en la línea"""
        last_cr = self.source_code.rfind('\n', 0, token.lexpos)
        if last_cr < 0:
            last_cr = 0
        column = (token.lexpos - last_cr)
        return column

    def _check_function_call(self, call_expr, line):
        """Verifica una llamada a función"""
        func_name = call_expr.callee.name
        
        # No verificar funciones built-in como print, input, len
        builtin_functions = ['print', 'input', 'len', 'range', 'int', 'str', 'float']
        if func_name in builtin_functions:
            return
            
        # SOLUCIÓN: Verificar si la función ya está pre-registrada
        if func_name in self.user_defined_functions or func_name in self.known_functions:
            return
            
        # Verificar si la función está definida en nuestra tabla de símbolos o es conocida
        symbol = self.symbol_table.resolve(func_name)
        if not symbol and func_name not in self.user_defined_functions and func_name not in self.known_functions:
            error_msg = f"Error semántico en línea {line}: Función '{func_name}' no está definida"
            # Verificar si este error ya ha sido reportado
            if error_msg not in self.semantic_errors:
                self.semantic_errors.append(error_msg)

    # Añadir una función de ayuda para la depuración
    def debug_production(self, p, rule_name):
        """Ayuda a depurar las producciones"""
        print(f"Debug - Regla {rule_name}: Tokens = {[str(x) for x in p[1:]]}")

    def debug_token_stream(self, text):
        """Método para debuggear el flujo de tokens"""
        print("\nDEBUG: Analizando flujo de tokens")
        print("=====================================")
        lexer = PLYLexer(text)
        while True:
            tok = lexer.token()
            if not tok:
                break
            print(f"Token: {tok.type:10} | Valor: {tok.value:20} | Línea: {tok.lineno}")
        print("=====================================\n")

    def parse(self, text, lexer=None):
        """Analiza el texto y construye el AST"""
        self.source_lines = text.splitlines()
        self.semantic_errors = []
        
        # No reiniciar la tabla de símbolos completamente para preservar las funciones pre-registradas
        if not hasattr(self, 'symbol_table') or self.symbol_table is None:
            self.symbol_table = SymbolTable()
        
        try:
            # Asegurar que estamos en el nivel de indentación correcto para funciones definidas
            has_functions = 'def ' in text
            if has_functions and self.function_contexts:
                self.indent_level = 4  # Nivel típico para una definición de función
            
            # Si el lexer tiene errores, no continuar con el parsing
            if lexer and (not lexer.valid_code or lexer.errors):
                self.semantic_errors.extend(lexer.errors)
                return None
                
            # Si no se proporciona un lexer, crear uno nuevo
            if not lexer:
                lexer = PLYLexer(text)
                # Asegurarse de que no haya errores léxicos
                while lexer.token():
                    pass
                if not lexer.valid_code or lexer.errors:
                    self.semantic_errors.extend(lexer.errors)
                    return None
                # Reiniciar el lexer para el parsing
                lexer = PLYLexer(text)
            
            # Parsear el texto
            ast = self.parser.parse(input=text, lexer=lexer.lexer)
            
            # Comprobar si hay errores de sintaxis
            if self.semantic_errors:
                return None
                
            # Comprobar si hay errores semánticos
            if self.semantic_errors:
                self.semantic_errors.extend(self.semantic_errors)
                return None
            
            return ast
        except Exception as e:
            self.semantic_errors.append(f"Error inesperado: {str(e)}")
            return None

    def _is_in_function_context(self):
        """Determina si el código actual está dentro de una función."""
        # Verificar si estamos dentro de un bloque de función basado en la pila de contextos
        if self.function_contexts:
            return True
        
        # Verificar basado en la indentación y tabla de símbolos
        if self.indent_level > 0:
            # Buscar en la tabla de símbolos para funciones definidas
            for symbol in self.symbol_table.symbols:
                if symbol.kind == 'function':
                    return True
        
        return False
        
    def _enter_function_context(self, function_name):
        """Registra la entrada a un bloque de función."""
        self.function_contexts.append(function_name)
        
    def _exit_function_context(self):
        """Registra la salida de un bloque de función."""
        if self.function_contexts:
            return self.function_contexts.pop()
        return None
        
    def _update_indent_level(self, p):
        """Actualiza el nivel de indentación basado en tokens INDENT/DEDENT."""
        if hasattr(p, 'lexer') and hasattr(p.lexer, 'last_tokens'):
            for token in p.lexer.last_tokens:
                if token.type == 'INDENT':
                    self.indent_level += 1
                elif token.type == 'DEDENT':
                    self.indent_level = max(0, self.indent_level - 1)
                    # Si salimos de un nivel de indentación, podríamos estar saliendo de una función
                    if self.indent_level == 0 and self.function_contexts:
                        self._exit_function_context()

    def _check_variable_reference(self, var_node, line):
        """Verifica una referencia a variable"""
        if not isinstance(var_node, Identifier):
            return
            
        var_name = var_node.name
        # No verificar palabras clave o literales booleanos/None
        if var_name in self.keywords or var_name in ['True', 'False', 'None']:
            return
            
        # Verificar si la variable está definida
        if not self.symbol_table.resolve(var_name):
            error_msg = f"Error semántico en línea {line}: Variable '{var_name}' no está definida"
            if error_msg not in self.semantic_errors:
                self.semantic_errors.append(error_msg)

    # Error: Indentación incorrecta en el cuerpo de la función
    def p_function_def_missing_indent(self, p):
        '''function_def : KEYWORD ID LPAREN parameter_list RPAREN return_type COLON NEWLINE statement_list'''
        if p[1] == 'def':
            # Detectamos una función sin indentación correcta
            line = p.lineno(8) + 1 if hasattr(p, 'lineno') else 0  # Línea después del NEWLINE
            if line > 0 and line <= len(self.source_lines):
                code_line = self.source_lines[line - 1]
                
                error_handler.add_error(CompilerError(
                    type=ErrorType.SYNTACTIC,
                    line=line,
                    message="Indentación incorrecta en el cuerpo de la función",
                    code_line=code_line,
                    column=0,  # Al principio de la línea
                    suggestion="El cuerpo de la función debe estar indentado (usualmente con 4 espacios o un tabulador)"
                ))
                self.valid_code = False
            
            # Intentar recuperarse del error
            name = p[2]
            params = p[4] if p[4] else []
            return_type = 'void'
            if p[6]:
                return_type = p[6].name
            body = p[9] if p[9] else []
            
            p[0] = FunctionDef(name, params, return_type, body)

def print_ast(node, indent=0):
    """Imprime el AST de forma legible"""
    prefix = "  " * indent
    
    if isinstance(node, Program):
        print(f"{prefix}Program")
        for stmt in node.statements:
            print_ast(stmt, indent + 1)
    
    elif isinstance(node, FunctionDef):
        print(f"{prefix}FunctionDef: {node.name}")
        print(f"{prefix}  Parameters: {[f'{p.name}: {p.type.name if p.type else "any"}' for p in node.params]}")
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
        print(f"{prefix}  Value:", end="")
        print_ast(node.value, 0)
    
    elif isinstance(node, BinaryExpr):
        print(f"{prefix}BinaryExpr: {node.operator}")
        print(f"{prefix}  Left:", end="")
        print_ast(node.left, 0)
        print(f"{prefix}  Right:", end="")
        print_ast(node.right, 0)
    
    elif isinstance(node, CallExpr):
        print(f"{prefix}Call: {node.callee.name}")
        print(f"{prefix}  Arguments:")
        for arg in node.arguments:
            print_ast(arg, indent + 1)
    
    elif isinstance(node, Identifier):
        print(f"{prefix}Identifier({node.name})", end="")
    
    elif isinstance(node, Literal):
        print(f"{prefix}Literal({node.value}: {node.type_name})", end="")
    
    else:
        print(f"{prefix}Unknown node type: {type(node)}")

if __name__ == "__main__":
    test_ast()