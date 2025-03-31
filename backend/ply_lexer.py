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
known_functions = ['print', 'len', 'range', 'int', 'str', 'float', 'list', 'dict', 'set', 'tuple']

# Definición de tokens para PLY - solo los que realmente usamos
tokens = (
    'ID', 'NUMBER', 'STRING', 
    'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'MOD',
    'EQ', 'NE', 'LT', 'GT', 'LE', 'GE',
    'LPAREN', 'RPAREN', 
    'COMMA', 'COLON', 'ARROW',
    'ASSIGN', 'NEWLINE', 'INDENT', 'DEDENT',
    'KEYWORD'
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
    t_LPAREN = r'\('
    t_RPAREN = r'\)'
    t_COMMA = r','
    t_COLON = r':'
    t_ASSIGN = r'='
    t_ARROW = r'->'
    
    # Ignorar espacios y tabs (excepto para indentación)
    t_ignore = ' \t'
    
    def __init__(self, text):
        # Configuración del lexer
        self.lexer = lex.lex(module=self)
        self.lexer.input(text)
        self.errors = []
        self.source_lines = text.splitlines()
        
        # Variables para manejar indentación
        self.indent_stack = [0]
        self.tokens_queue = []
    
    def t_ID(self, t):
        r'[a-zA-Z_][a-zA-Z0-9_]*'
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
        r'(\"[^\"]*\"|\'[^\']*\'|f\"[^\"]*\"|f\'[^\']*\')'
        # Eliminar comillas
        t.value = t.value[1:-1]
        return t
    
    def t_NEWLINE(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)
        
        # Calcular indentación
        if t.lexer.lexpos < len(t.lexer.lexdata):
            pos = t.lexer.lexpos
            while pos < len(t.lexer.lexdata) and t.lexer.lexdata[pos] in ' \t':
                pos += 1
            
            # Si la línea no está vacía y no es un comentario
            if pos < len(t.lexer.lexdata) and t.lexer.lexdata[pos] != '\n' and t.lexer.lexdata[pos:pos+1] != '#':
                indent = pos - t.lexer.lexpos
                
                # Comparar con el nivel de indentación actual
                if indent > self.indent_stack[-1]:
                    # Aumentar indentación
                    self.indent_stack.append(indent)
                    self.tokens_queue.append(('INDENT', 'INDENT', t.lexer.lineno))
                elif indent < self.indent_stack[-1]:
                    # Disminuir indentación
                    while indent < self.indent_stack[-1]:
                        self.indent_stack.pop()
                        self.tokens_queue.append(('DEDENT', 'DEDENT', t.lexer.lineno))
                    
                    # Verificar que la indentación coincida con un nivel anterior
                    if indent != self.indent_stack[-1]:
                        self.errors.append(f"Error en línea {t.lexer.lineno}: Indentación inconsistente")
        
        return t
    
    def t_COMMENT(self, t):
        r'\#.*'
        pass  # Ignorar comentarios
    
    def t_error(self, t):
        error_msg = f"Error en línea {t.lexer.lineno}: Carácter ilegal '{t.value[0]}'"
        self.errors.append(error_msg)
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
        
        # Si no hay tokens en la cola, obtener el siguiente token del lexer
        tok = self.lexer.token()
        
        # Verificar errores tipográficos comunes
        if tok and tok.type == 'ID' and tok.value == 'pritn':
            self.errors.append(f"Error en línea {tok.lineno}: Posible error tipográfico: 'pritn'. ¿Querías decir 'print'?")
        
        return tok
