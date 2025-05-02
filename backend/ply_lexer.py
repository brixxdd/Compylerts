import ply.lex as lex
from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional
import re
from error_handler import error_handler, CompilerError, ErrorType

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
    
    def __init__(self, source_code: str):
        self.source_code = source_code
        self.source_lines = source_code.splitlines()
        self.lexer = lex.lex(module=self)
        self.lexer.input(source_code)
        self.valid_code = True
        self.last_token = None
        self.last_tokens = []
        self.max_tokens_history = 10
        
        # Inicializar el lexer
        self.check_unclosed_delimiters()
        self.check_invalid_characters()
        
        # Variables para manejar indentación
        self.indent_stack = [0]
        self.tokens_queue = []
        self.paren_stack = []  # Pila para rastrear paréntesis
        self.bracket_stack = []  # Nueva pila para rastrear corchetes
        self.index = 0
        self.previous_line = 1
        self.previous_column = 0

    def check_unclosed_delimiters(self):
        """Verifica delimitadores sin cerrar"""
        for i, line in enumerate(self.source_lines, 1):
            # Verificar paréntesis
            if '(' in line and ')' not in line[line.find('('):]:
                col = line.find('(')
                error_handler.add_error(CompilerError(
                    type=ErrorType.SYNTACTIC,
                    line=i,
                    message="Paréntesis sin cerrar",
                    code_line=line,
                    column=col,
                    suggestion="Agrega el paréntesis de cierre ')'"
                ))
                self.valid_code = False
            
            # Verificar corchetes
            if '[' in line and ']' not in line[line.find('['):]:
                col = line.find('[')
                error_handler.add_error(CompilerError(
                    type=ErrorType.SYNTACTIC,
                    line=i,
                    message="Corchete sin cerrar",
                    code_line=line,
                    column=col,
                    suggestion="Agrega el corchete de cierre ']'"
                ))
                self.valid_code = False

    def check_invalid_characters(self):
        """Verifica caracteres inválidos en el código"""
        invalid_chars = '@#$&~`'
        for i, line in enumerate(self.source_lines, 1):
            # Ignorar caracteres inválidos en comentarios
            comment_pos = line.find('#')
            check_line = line if comment_pos == -1 else line[:comment_pos]
            
            for char in invalid_chars:
                if char == '#':  # Ignorar # ya que es para comentarios
                    continue
                if char in check_line:
                    col = check_line.index(char)
                    error_handler.add_error(CompilerError(
                        type=ErrorType.LEXICAL,
                        line=i,
                        message=f"Carácter no válido '{char}'",
                        code_line=line,
                        column=col,
                        suggestion=f"El carácter '{char}' no está permitido en el lenguaje"
                    ))
                    self.valid_code = False

    def token(self):
        """Método requerido por PLY para obtener el siguiente token"""
        tok = self.lexer.token()
        if tok:
            self.last_token = tok
            self.last_tokens.append(tok)
            if len(self.last_tokens) > self.max_tokens_history:
                self.last_tokens.pop(0)
        return tok

    def t_STRING(self, t):
        r'(?<!f)("([^"\n]|\\")*"|\'([^\'\n]|\\\')*\')'
        # Las comillas están bien cerradas
        t.value = t.value[1:-1]  # Remover las comillas
        return t

    def t_UNCLOSED_STRING(self, t):
        r'(?<!f)("([^"\n]|\\")*((\n|$))|\'([^\'\n]|\\\')*((\n|$)))'
        # Si llegamos aquí, es porque encontramos un string que empieza con comilla pero no termina correctamente
        quote_type = '"' if t.value[0] == '"' else "'"
        content = t.value[1:]  # El contenido sin la comilla inicial
        error_msg = f"""Error léxico en línea {t.lexer.lineno}: String sin cerrar correctamente
En el código:
    {self.source_lines[t.lexer.lineno - 1]}
    {' ' * self._find_column(t)}^ Falta cerrar el string con {quote_type}
Sugerencia: El string debe terminar con la misma comilla con la que inicia.
Para corregir este error, añade {quote_type} al final del string:
    nombre = {quote_type}{content.strip()}{quote_type}
También verifica si hay una coma faltante después del string."""
        error_handler.add_error(CompilerError(
            type=ErrorType.LEXICAL,
            line=t.lexer.lineno,
            message=error_msg,
            code_line=self.source_lines[t.lexer.lineno - 1],
            column=self._find_column(t),
            suggestion="Revisa los strings y asegúrate de que estén correctamente cerrados"
        ))
        self.valid_code = False
        # Avanzar hasta el final de la línea
        while t.lexer.lexpos < len(t.lexer.lexdata) and t.lexer.lexdata[t.lexer.lexpos] != '\n':
            t.lexer.lexpos += 1
        return None

    def t_ID(self, t):
        r'[a-zA-Z_][a-zA-Z0-9_]*'
        # Verificar si es una palabra clave
        if t.value in self.keywords:
            t.type = 'KEYWORD'
        else:
            # Verificar si es un identificador no definido que parece una función
            next_char = self.lexer.lexdata[t.lexpos + len(t.value):t.lexpos + len(t.value) + 1]
            if next_char == '(':
                # Lista de funciones conocidas
                known_funcs = ['print', 'input', 'len', 'str', 'int', 'float', 'list', 'range']
                
                # Verificar si la función está definida
                if t.value not in self.keywords and t.value not in known_funcs:
                    # Verificar si puede ser un error tipográfico de una función conocida
                    possible_typos = []
                    for func in known_funcs:
                        # Calcular la distancia de Levenshtein para determinar similitud
                        if self._is_similar(t.value, func):
                            possible_typos.append(func)
                    
                    # Sugerencia específica si parece un error tipográfico
                    suggestion = f"Asegúrate de que la función '{t.value}' esté definida antes de usarla"
                    if possible_typos:
                        suggestion = f"¿Quisiste decir '{possible_typos[0]}'? Asegúrate de escribir correctamente el nombre de la función."
                    
                    error_handler.add_error(CompilerError(
                        type=ErrorType.SEMANTIC,
                        line=t.lineno,
                        message=f"Función '{t.value}' no está definida",
                        code_line=self.source_lines[t.lineno - 1],
                        column=t.lexpos - sum(len(l) + 1 for l in self.source_lines[:t.lineno - 1]),
                        suggestion=suggestion
                    ))
                    self.valid_code = False
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
                        error_handler.add_error(CompilerError(
                            type=ErrorType.SYNTACTIC,
                            line=self.lineno,
                            message=f"Indentación inconsistente. Se esperaba un nivel de {expected_indent} espacios.",
                            code_line=self.source_lines[self.lineno - 1],
                            column=self._find_column(t),
                            suggestion=f"Revisa la indentación del código para que sea consistente"
                        ))
        return t
    
    def t_COMMENT(self, t):
        r'\#.*'
        # Simplemente ignorar el comentario sin hacer ninguna validación
        return None
    
    def t_error(self, t):
        # Ignorar caracteres inválidos dentro de comentarios
        line = self.source_lines[t.lineno - 1]
        if '#' in line and t.lexpos > line.find('#'):
            t.lexer.skip(1)
            return

        error_handler.add_error(CompilerError(
            type=ErrorType.LEXICAL,
            line=t.lineno,
            message=f"Carácter no válido '{t.value[0]}'",
            code_line=line,
            column=t.lexpos - sum(len(l) + 1 for l in self.source_lines[:t.lineno - 1]),
            suggestion="Revisa los caracteres permitidos en el lenguaje"
        ))
        self.valid_code = False
        t.lexer.skip(1)
    
    def t_ARROW(self, t):
        r'->'
        return t

    def t_COMMA(self, t):
        r','
        t.lexer.last_token = t
        return t

    def t_LPAREN(self, t):
        r'\('
        self.paren_stack.append((t.lexer.lineno, self._find_column(t)))
        return t

    def t_RPAREN(self, t):
        r'\)'
        if not self.paren_stack:
            line = self.source_lines[t.lexer.lineno - 1]
            column = self._find_column(t)
            error_handler.add_error(CompilerError(
                type=ErrorType.SYNTACTIC,
                line=t.lexer.lineno,
                message="Paréntesis de cierre sin coincidencia",
                code_line=line,
                column=column,
                suggestion="Agrega el paréntesis de apertura '(' correspondiente"
            ))
            self.valid_code = False
        else:
            self.paren_stack.pop()
        return t

    def t_LBRACKET(self, t):
        r'\['
        self.bracket_stack.append((t.lexer.lineno, self._find_column(t)))
        return t

    def t_RBRACKET(self, t):
        r'\]'
        if not self.bracket_stack:
            line = self.source_lines[t.lexer.lineno - 1]
            column = self._find_column(t)
            error_handler.add_error(CompilerError(
                type=ErrorType.SYNTACTIC,
                line=t.lexer.lineno,
                message="Corchete de cierre sin coincidencia",
                code_line=line,
                column=column,
                suggestion="Agrega el corchete de apertura '[' correspondiente"
            ))
            self.valid_code = False
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

    def _is_similar(self, s1, s2):
        """Determina si dos cadenas son similares (posible error tipográfico)"""
        # Implementación simple: si tienen la misma longitud y difieren en 1-2 caracteres
        if abs(len(s1) - len(s2)) > 1:
            return False
            
        # Si una es subcadena de la otra
        if s1 in s2 or s2 in s1:
            return True
            
        # Contar diferencias
        if len(s1) == len(s2):
            differences = sum(1 for a, b in zip(s1, s2) if a != b)
            return differences <= 2
            
        # Intentar alinear y contar diferencias
        if len(s1) < len(s2):
            s1, s2 = s2, s1  # s1 siempre es la más larga
            
        # Verificar si quitando/añadiendo un carácter son iguales
        for i in range(len(s1)):
            if s1[:i] + s1[i+1:] == s2:
                return True
                
        return False
