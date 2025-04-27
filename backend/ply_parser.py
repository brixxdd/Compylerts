import ply.yacc as yacc
from ply_lexer import PLYLexer, known_functions
from ast_nodes import (
    Program, ExpressionStmt, AssignmentStmt, ReturnStmt, FunctionDef, IfStmt,
    BinaryExpr, UnaryExpr, GroupingExpr, Literal, Identifier, CallExpr,
    Parameter, Type, BinaryOp, UnaryOp, ForStmt
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
    
    def __init__(self, source_code=None):
        """Inicializa el parser"""
        self.parser = yacc.yacc(module=self, debug=False)
        self.errors = []
        self.source_lines = source_code.splitlines() if source_code else []
        self.user_defined_functions = set()
        self.known_functions = ['print', 'input', 'len']
        self.valid_code = True
        self.symbol_table = SymbolTable()
        self.semantic_errors = []
    
    # ======================================================================
    # REGLAS BNF PARA EL LENGUAJE
    # ======================================================================

    # <program> ::= <statement_list>
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
    
    # <statement_list> ::= <statement> | <statement_list> <statement>
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
        if p[1] == '\n':
            p[0] = None
        else:
            p[0] = p[1]
    
    # <expression_statement> ::= <expression> NEWLINE
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
            if len(p) > 3:
                p[0] = ReturnStmt(p[2])
            else:
                p[0] = ReturnStmt(None)
    
    # <compound_statement> ::= <function_def> | <if_statement> | <for_statement>
    def p_compound_statement(self, p):
        '''compound_statement : function_def
                             | if_statement
                             | for_statement'''
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
    
    # <if_statement> ::= KEYWORD <expression> COLON NEWLINE INDENT <statement_list> DEDENT
    #                  | KEYWORD <expression> COLON NEWLINE INDENT <statement_list> DEDENT KEYWORD COLON NEWLINE INDENT <statement_list> DEDENT
    def p_if_statement(self, p):
        '''if_statement : if_without_else
                       | if_with_else'''
        p[0] = p[1]

    def p_if_without_else(self, p):
        '''if_without_else : KEYWORD expression COLON NEWLINE INDENT statement_list DEDENT'''
        condition = p[2]
        then_branch = p[6]
        p[0] = IfStmt(condition, then_branch, None)

    def p_if_with_else(self, p):
        '''if_with_else : KEYWORD expression COLON NEWLINE INDENT statement_list DEDENT KEYWORD COLON NEWLINE INDENT statement_list DEDENT'''
        if p[1] == 'if' and p[8] == 'else':
            condition = p[2]
            then_branch = p[6]
            else_branch = p[12]
            p[0] = IfStmt(condition, then_branch, else_branch)
        else:
            # Error de sintaxis si no son 'if' y 'else'
            error_msg = f"Error de sintaxis: se esperaba 'if' y 'else', se encontró '{p[1]}' y '{p[8]}'"
            self.errors.append(error_msg)
            p[0] = None
    
    # <for_statement> ::= KEYWORD ID KEYWORD expression COLON NEWLINE INDENT <statement_list> DEDENT
    def p_for_statement(self, p):
        '''for_statement : KEYWORD ID KEYWORD expression COLON NEWLINE INDENT statement_list DEDENT'''
        if p[1] == 'for' and p[3] == 'in':
            variable = Identifier(p[2])
            iterable = p[4]
            body = p[8]
            p[0] = ForStmt(variable, iterable, body)
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
        if isinstance(p[1], str):  # ID
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
        print(f"\nDEBUG CALL:")
        print(f"Función llamada: {p[1]}")
        func_name = p[1]
        args = [] if len(p) == 4 else p[3]
        
        # Manejo especial para funciones built-in como print
        if func_name in ['print', 'input', 'len']:
            p[0] = CallExpr(Identifier(func_name), args)
            return
        
        # Verificar si la función existe y el número de argumentos
        symbol = self.symbol_table.resolve(func_name)
        if not symbol:
            self.semantic_errors.append(
                f"Error semántico en línea {p.lexer.lineno}: "
                f"Función '{func_name}' no está definida"
            )
            p[0] = CallExpr(Identifier(func_name), args)
            return
        
        if symbol.kind != 'function':
            self.semantic_errors.append(
                f"Error semántico en línea {p.lexer.lineno}: "
                f"'{func_name}' no es una función"
            )
            p[0] = CallExpr(Identifier(func_name), args)
            return
        
        # No verificar número de argumentos para print
        if func_name != 'print':
            expected_args = len(symbol.parameters) if symbol.parameters else 0
            received_args = len(args)
            if expected_args != received_args:
                self.semantic_errors.append(
                    f"Error semántico en línea {p.lexer.lineno}: "
                    f"La función '{func_name}' espera {expected_args} argumentos "
                    f"pero recibió {received_args}"
                )
        
        p[0] = CallExpr(Identifier(func_name), args)
    
    # <arguments> ::= <expression> | <arguments> COMMA <expression>
    def p_arguments(self, p):
        '''arguments : expression
                     | arguments COMMA expression'''
        if len(p) == 2:
            p[0] = [p[1]]
        else:
            p[0] = p[1] + [p[3]]
    
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
        if p:
            line = self.source_lines[p.lineno - 1] if self.source_lines else ""
            column = self._find_column(p)
            
            # Detectar el caso específico de parámetros faltantes
            if p.type == 'RPAREN' and hasattr(p.lexer, 'last_token') and p.lexer.last_token.type == 'COMMA':
                # Obtener el nombre de la función que se está llamando
                func_name = None
                if hasattr(p.lexer, 'last_tokens'):
                    for i in range(len(p.lexer.last_tokens)-1, -1, -1):
                        if p.lexer.last_tokens[i].type == 'ID':
                            if i > 0 and p.lexer.last_tokens[i-1].type == 'ASSIGN':
                                func_name = p.lexer.last_tokens[i+1].value
                                break
                            else:
                                func_name = p.lexer.last_tokens[i].value
                                break

                func_name = func_name if func_name else 'suma'
                error_msg = f"""Error de sintaxis en línea {p.lineno}: Parámetro faltante
En el código:
    {line}
    {' ' * column}^ No se permite una coma al final sin un argumento

Sugerencia: La función '{func_name}' espera otro argumento después de la coma
Ejemplo correcto: {func_name}(5, 10)"""
                self.errors = [error_msg]
            else:
                error_msg = f"""Error de sintaxis en línea {p.lineno}: Token inesperado '{p.value}'
En el código:
    {line}
    {' ' * column}^ Aquí"""
                self.errors = [error_msg]
            
            self.valid_code = False
        else:
            error_msg = "Error de sintaxis: entrada inesperada al final del archivo"
            self.errors = [error_msg]
            self.valid_code = False

    def _find_column(self, token):
        """Encuentra la columna donde está un token"""
        if token is None or not hasattr(token, 'lexpos'):
            return 0
        if not hasattr(token.lexer, 'lexdata'):
            return len(self.source_lines[token.lineno - 1]) if self.source_lines else 0
        input = token.lexer.lexdata
        last_cr = input.rfind('\n', 0, token.lexpos)
        if last_cr < 0:
            last_cr = 0
        return token.lexpos - last_cr

    def _is_function_def_context(self, token):
        """Verifica si estamos en el contexto de una definición de función"""
        if not hasattr(token.lexer, 'last_tokens'):
            return False
        
        # Buscar los últimos tokens para ver si estamos después de una definición de función
        last_tokens = getattr(token.lexer, 'last_tokens', [])
        expected_sequence = ['KEYWORD', 'ID', 'LPAREN', 'RPAREN', 'ARROW', 'ID']
        
        if len(last_tokens) >= len(expected_sequence):
            recent_tokens = [t.type for t in last_tokens[-len(expected_sequence):]]
            return recent_tokens == expected_sequence and last_tokens[-6].value == 'def'
        return False

    # Modificar el método que verifica llamadas a funciones para evitar duplicados
    def _check_function_call(self, call_expr, line):
        """Verifica una llamada a función"""
        func_name = call_expr.callee.name
        error_msg = f"Error semántico en línea {line}: Función '{func_name}' no está definida"
        
        if not self.symbol_table.resolve(func_name) and func_name not in ['print', 'input', 'len']:
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
        self.errors = []
        self.semantic_errors = []
        self.symbol_table = SymbolTable()
        
        try:
            # Si el lexer tiene errores, no continuar con el parsing
            if not lexer.valid_code or lexer.errors:
                self.errors.extend(lexer.errors)
                return None
                
            ast = self.parser.parse(input=text, lexer=lexer)
            
            if self.errors:
                return None
            
            return ast
        except Exception as e:
            self.errors.append(f"Error inesperado: {str(e)}")
            return None

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