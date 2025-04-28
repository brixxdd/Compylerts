import ply.lex as lex
from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional
import re

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
    FSTRING = auto()

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
    'FSTRING',  # Debe estar primero
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
        self.errors = []
        self.source_lines = text.splitlines()
        self.valid_code = True
        self.lineno = 1  # Añadir contador de línea
        
        # Lista para mantener los últimos tokens
        self.last_tokens = []
        self.last_token = None
        self.lexer.last_tokens = []
        self.lexer.last_token = None
        
        # Preprocesar el texto antes de pasarlo al lexer
        processed_text = self.preprocess_fstrings(text)
        self.lexer.input(processed_text)
        
        # Variables para manejar indentación
        self.indent_stack = [0]
        self.tokens_queue = []
        self.paren_stack = []  # Pila para rastrear paréntesis
        self.bracket_stack = []  # Nueva pila para rastrear corchetes
    
    def t_STRING(self, t):
        r'(?<!f)("([^"\n]|\\")*"|\'([^\'\n]|\\\')*\')'
        # Las comillas están bien cerradas
        t.value = t.value[1:-1]  # Remover las comillas
        return t

    def t_UNCLOSED_STRING(self, t):
        r'(?<!f)("([^"\n]|\\")*|\'([^\'\n]|\\\')*)'
        # Si llegamos aquí, es porque encontramos un string que empieza con comilla pero no termina correctamente
        quote_type = '"' if t.value[0] == '"' else "'"
        content = t.value[1:]  # El contenido sin la comilla inicial
        error_msg = f"""Error léxico en línea {t.lexer.lineno}: String sin cerrar correctamente
En el código:
    {self.source_lines[t.lexer.lineno - 1]}
    {' ' * self._find_column(t)}^ String '{content}' comienza con {quote_type} pero no se cierra
Sugerencia: Asegúrate de cerrar el string con la misma comilla ({quote_type}):
    nombre = {quote_type}{content}{quote_type}"""
        self.errors.append(error_msg)
        self.valid_code = False
        # Avanzar hasta el final de la línea
        while t.lexer.lexpos < len(t.lexer.lexdata) and t.lexer.lexdata[t.lexer.lexpos] != '\n':
            t.lexer.lexpos += 1
        return None

    def t_ID(self, t):
        r'[a-zA-Z_][a-zA-Z0-9_]*'
        if not all(ord(c) < 128 for c in t.value):
            self.errors.append(f"Error en línea {t.lexer.lineno}: El identificador '{t.value}' contiene caracteres no ASCII.")
            self.valid_code = False
            return None
        
        # Verificar si es una palabra clave
        if t.value in self.keywords:
            t.type = 'KEYWORD'
            print(f"\nDEBUG KEYWORD: Found keyword '{t.value}'")  # Debug info
        return t
    
    def t_NUMBER(self, t):
        r'\d+(\.\d+)?'
        if '.' in t.value:
            t.value = float(t.value)
        else:
            t.value = int(t.value)
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
        # Solo mostrar error de carácter no válido si no es parte de un string sin cerrar
        if not (t.value.startswith('"') or t.value.startswith("'")):
            self.errors.append(f"""Error léxico en línea {t.lexer.lineno}: Carácter no válido '{t.value[0]}'
En el código:
    {self.source_lines[t.lexer.lineno - 1]}
    {' ' * self._find_column(t)}^ Aquí se encontró el carácter no válido""")
        self.valid_code = False
        t.lexer.skip(1)
    
    def token(self):
        """Método requerido por PLY para obtener el siguiente token"""
        if self.tokens_queue:
            token_type, token_value, lineno = self.tokens_queue.pop(0)
            tok = lex.LexToken()
            tok.type = token_type
            tok.value = token_value
            tok.lineno = lineno
            tok.lexpos = 0
            
            # Debug info
            print(f"\nDEBUG TOKEN (from queue):")
            print(f"Token: {tok.type}")
            print(f"Valor: {tok.value}")
            print(f"Línea: {tok.lineno}")
            
            # Guardar este token
            self.last_token = tok
            self.last_tokens.append(tok)
            self.lexer.last_token = tok
            self.lexer.last_tokens.append(tok)
            # Mantener solo los últimos 10 tokens
            if len(self.last_tokens) > 10:
                self.last_tokens.pop(0)
            if len(self.lexer.last_tokens) > 10:
                self.lexer.last_tokens.pop(0)
            
            return tok
        
        tok = self.lexer.token()
        if tok:
            # Debug info
            print(f"\nDEBUG TOKEN (from lexer):")
            print(f"Token: {tok.type}")
            print(f"Valor: {tok.value}")
            print(f"Línea: {tok.lineno}")
            
            # Guardar este token
            self.last_token = tok
            self.last_tokens.append(tok)
            self.lexer.last_token = tok
            self.lexer.last_tokens.append(tok)
            # Mantener solo los últimos 10 tokens
            if len(self.last_tokens) > 10:
                self.last_tokens.pop(0)
            if len(self.lexer.last_tokens) > 10:
                self.lexer.last_tokens.pop(0)
            
            return tok
        return None

    def t_ARROW(self, t):
        r'->'
        return t

    def t_COMMA(self, t):
        r','
        t.lexer.last_token = t
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

    def is_fstring(self, value):
        return hasattr(value, 'is_fstring')

    def get_fstring_content(self, value):
        return value.content if self.is_fstring(value) else value

    def preprocess_fstrings(self, text):
        """Convierte f-strings en strings normales preservando las comillas"""
        def replace_fstring(match):
            # Obtener el contenido completo incluyendo las comillas
            full_match = match.group(0)
            # Simplemente quitar la 'f' del inicio
            return full_match[1:]
        
        pattern = r'f"[^"]*"|f\'[^\']*\''
        processed_text = re.sub(pattern, replace_fstring, text)
        print(f"\nDEBUG Preprocessor:")
        print(f"Texto original: {text}")
        print(f"Texto procesado: {processed_text}")
        return processed_text
    
    def input(self, text):
        """Sobrescribir el método input para preprocesar el texto"""
        processed_text = self.preprocess_fstrings(text)
        self.lexer.input(processed_text)

    def _find_column(self, token):
        """Encuentra la columna donde está un token"""
        if token is None:
            return 0
        last_cr = token.lexer.lexdata.rfind('\n', 0, token.lexpos)
        if last_cr < 0:
            last_cr = 0
        return token.lexpos - last_cr
