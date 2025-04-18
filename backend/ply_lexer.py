import ply.lex as lex
from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional

# Definir nuestros propios tipos de token
class TokenType(Enum):
    IDENTIFIER = auto()
    NUMBER = auto()
    STRING = auto()
    OPERATOR = auto()
    DELIMITER = auto()
    KEYWORD = auto()
    TYPE_HINT = auto()
    NEWLINE = auto()
    INDENT = auto()
    DEDENT = auto()
    EOF = auto()
    ERROR = auto()
    TEMPLATE_STRING = auto()
    ARROW = auto()
    ASYNC = auto()
    AWAIT = auto()
    TRAILING_COMMA = auto()

@dataclass
class Position:
    line: int
    column: int

@dataclass
class Token:
    type: TokenType
    value: str
    position: Position

# Funciones conocidas para sugerencias
known_functions = ['print', 'len', 'range', 'int', 'str', 'float', 'list', 'dict', 'set', 'tuple', 'input']

# Definición de tokens para PLY - solo los que realmente usamos
tokens = (
    'ID', 'NUMBER', 'STRING', 
    'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'MOD',
    'EQ', 'NE', 'LT', 'GT', 'LE', 'GE',
    'LPAREN', 'RPAREN', 
    'LBRACKET', 'RBRACKET',
    'COMMA', 'COLON',
    'ASSIGN', 'NEWLINE', 'INDENT', 'DEDENT',
    'KEYWORD', 'ARROW'
)

class PLYLexer:
    """Implementación directa de un lexer PLY"""
    
    # Lista de tokens - debe ser un atributo de clase para PLY
    tokens = tokens
    
    # Lista de palabras clave de Python
    keywords = {
        'def', 'if', 'else', 'elif', 'while', 'for', 'in', 'return', 'break', 
        'continue', 'class', 'import', 'from', 'as', 'try', 'except', 'finally',
        'with', 'not', 'and', 'or', 'is', 'None', 'True', 'False'
    }
    
    # Reglas para tokens simples
    t_PLUS = r'\+'
    t_MINUS = r'-'
    t_TIMES = r'\*'
    t_DIVIDE = r'/'
    t_MOD = r'%'
    t_EQ = r'=='
    t_NE = r'!='
    t_LT = r'<'
    t_GT = r'>'
    t_LE = r'<='
    t_GE = r'>='
    t_COLON = r':'
    t_ASSIGN = r'='
    
    # Ignorar espacios y tabs (excepto para indentación)
    t_ignore = ' \t'
    
    def __init__(self, text):
        # Configuración del lexer
        self.lexer = lex.lex(module=self)
        self.lexer.input(text)
        self.errors = []
        self.source_lines = text.splitlines()
        self.valid_code = True
        self.lineno = 1  # Añadir contador de línea
        
        # Variables para manejar indentación
        self.indent_stack = [0]
        self.tokens_queue = []
        self.paren_stack = []  # Pila para rastrear paréntesis
        self.bracket_stack = []  # Nueva pila para rastrear corchetes
    
    def t_ID(self, t):
        r'[a-zA-Z_][a-zA-Z0-9_]*'
        if not all(ord(c) < 128 for c in t.value):
            self.errors.append(f"Error en línea {t.lexer.lineno}: El identificador '{t.value}' contiene caracteres no ASCII.")
            self.valid_code = False
            return None
        
        # Verificar errores comunes de escritura
        common_typos = {
            'pritn': 'print',
            'pint': 'print',
            'pirnt': 'print',
            'lenght': 'length',
            'retrun': 'return',
            'retun': 'return',
            'inut': 'input',
            'inpt': 'input',
            'imput': 'input'
        }
        
        if t.value in common_typos:
            error_msg = f"""Error léxico en línea {t.lexer.lineno}: '{t.value}' no es una palabra clave o función válida
En el código:
    {self.source_lines[t.lexer.lineno - 1]}
    {' ' * self.source_lines[t.lexer.lineno - 1].find(t.value)}^ ¿Quisiste decir '{common_typos[t.value]}'?"""
            self.errors.append(error_msg)
            
            # Importante: NO establecer valid_code a False para permitir que el análisis continúe
            # En su lugar, corregir automáticamente el error para continuar
            t.value = common_typos[t.value]
        
        if t.value in self.keywords:
            t.type = 'KEYWORD'
        return t
    
    def t_NUMBER(self, t):
        r'\d+(\.\d+)?'
        if '.' in t.value:
            t.value = float(t.value)
        else:
            t.value = int(t.value)
        return t
    
    def t_STRING(self, t):
        r'\"[^\"]*\"|\'[^\']*\''
        t.value = t.value[1:-1]  # Eliminar las comillas
        return t
    
    def t_NEWLINE(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)
        self.lineno = t.lexer.lineno
        
        if t.lexer.lexpos < len(t.lexer.lexdata):
            pos = t.lexer.lexpos
            while pos < len(t.lexer.lexdata) and t.lexer.lexdata[pos] in ' \t':
                pos += 1
            
            if pos < len(t.lexer.lexdata) and t.lexer.lexdata[pos] != '\n' and t.lexer.lexdata[pos:pos+1] != '#':
                indent = pos - t.lexer.lexpos
                
                if indent > self.indent_stack[-1]:
                    self.indent_stack.append(indent)
                    self.tokens_queue.append(('INDENT', 'INDENT', self.lineno))
                elif indent < self.indent_stack[-1]:
                    while indent < self.indent_stack[-1]:
                        self.indent_stack.pop()
                        self.tokens_queue.append(('DEDENT', 'DEDENT', self.lineno))
                    
                    if indent != self.indent_stack[-1]:
                        expected_indent = self.indent_stack[-1]
                        self.errors.append(
                            f"Error en línea {self.lineno}: Indentación inconsistente. "
                            f"Se esperaba un nivel de {expected_indent} espacios."
                        )
        return t
    
    def t_COMMENT(self, t):
        r'\#.*'
        # Simplemente ignorar el comentario sin hacer ninguna validación
        return None
    
    def t_error(self, t):
        # Obtener la línea completa donde está el error
        line = self.source_lines[t.lexer.lineno - 1]
        column = t.lexpos - sum(len(l) + 1 for l in self.source_lines[:t.lexer.lineno - 1])
        
        error_msg = f"""Error léxico en línea {t.lexer.lineno}: Carácter no válido '{t.value[0]}'
En el código:
    {line}
    {' ' * column}^ Aquí se encontró el carácter no válido"""
        
        self.errors.append(error_msg)
        self.valid_code = False
        t.lexer.skip(1)
    
    def token(self):
        """Método requerido por PLY para obtener el siguiente token"""
        # Primero, verificar si hay tokens en la cola (INDENT/DEDENT)
        if self.tokens_queue:
            token_type, token_value, lineno = self.tokens_queue.pop(0)
            tok = lex.LexToken()
            tok.type = token_type
            tok.value = token_value
            tok.lineno = lineno
            tok.lexpos = 0
            return tok
        
        # Si no hay más tokens en el input, verificar paréntesis y corchetes sin cerrar
        tok = self.lexer.token()
        if not tok:
            # Verificar paréntesis sin cerrar
            if self.paren_stack:
                for line_no, pos in self.paren_stack:
                    if 0 <= line_no - 1 < len(self.source_lines):
                        line = self.source_lines[line_no - 1]
                        column = pos - sum(len(l) + 1 for l in self.source_lines[:line_no - 1])
                        self.errors.append(f"""Error sintáctico en línea {line_no}: Paréntesis sin cerrar
En el código:
    {line}
    {' ' * column}^ Falta el paréntesis de cierre ')'
Sugerencia: {line[:column+1]})""")
                    
            # Verificar corchetes sin cerrar
            if self.bracket_stack:
                for line_no, pos in self.bracket_stack:
                    if 0 <= line_no - 1 < len(self.source_lines):
                        line = self.source_lines[line_no - 1]
                        column = pos - sum(len(l) + 1 for l in self.source_lines[:line_no - 1])
                        self.errors.append(f"""Error sintáctico en línea {line_no}: Corchete sin cerrar
En el código:
    {line}
    {' ' * column}^ Falta el corchete de cierre ']'
Sugerencia: {line}]""")
                    
            if self.indent_stack[-1] > 0:
                while len(self.indent_stack) > 1:
                    self.indent_stack.pop()
                    self.tokens_queue.append(('DEDENT', 'DEDENT', self.lineno))
                return self.token()
        
        if tok:
            tok.lineno = self.lineno
        
        return tok

    def t_ARROW(self, t):
        r'->'
        return t

    def t_COMMA(self, t):
        r','
        return t

    def t_LPAREN(self, t):
        r'\('
        self.paren_stack.append((t.lexer.lineno, t.lexpos))
        return t

    def t_RPAREN(self, t):
        r'\)'
        if not self.paren_stack:
            line = self.source_lines[t.lexer.lineno - 1]
            column = t.lexpos - sum(len(l) + 1 for l in self.source_lines[:t.lexer.lineno - 1])
            self.errors.append(f"Error léxico en línea {t.lexer.lineno}: Paréntesis de cierre sin coincidencia")
        else:
            self.paren_stack.pop()
        return t

    def t_LBRACKET(self, t):
        r'\['
        self.bracket_stack.append((t.lexer.lineno, t.lexpos))
        return t

    def t_RBRACKET(self, t):
        r'\]'
        if not self.bracket_stack:
            line = self.source_lines[t.lexer.lineno - 1]
            column = t.lexpos - sum(len(l) + 1 for l in self.source_lines[:t.lexer.lineno - 1])
            self.errors.append(f"""Error sintáctico en línea {t.lexer.lineno}: Corchete de cierre sin coincidencia
En el código:
    {line}
    {' ' * column}^ No hay un corchete de apertura correspondiente""")
        else:
            self.bracket_stack.pop()
        return t

    def parse(self, text):
        """Analiza el texto y construye el AST"""
        self.source_lines = text.splitlines()
        self.errors = []
        self.valid_code = True
        
        try:
            self.lexer = PLYLexer(text)
            
            # Realizar el análisis léxico primero
            tokens = []
            while True:
                tok = self.lexer.token()
                if not tok:
                    break
                if tok.type == 'TRAILING_COMMA':
                    # Detener el análisis si encontramos una coma huérfana
                    return None
                tokens.append(tok)
            
            if not self.valid_code:
                return None
            
            # Continuar con el análisis sintáctico si no hay errores
            return self.parser.parse(tokens)
        except Exception as e:
            self.errors.append(f"Error inesperado: {str(e)}")
            return None
