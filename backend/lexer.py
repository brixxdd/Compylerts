import enum
import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
from colorama import init, Fore, Style

# Initialize colorama for colored output
init()

class TokenType(enum.Enum):
    """Comprehensive enumeration of token types"""
    KEYWORD = 'keyword'
    IDENTIFIER = 'identifier'
    STRING = 'string'
    NUMBER = 'number'
    OPERATOR = 'operator'
    DELIMITER = 'delimiter'
    COMMENT = 'comment'
    DECORATOR = 'decorator'
    TYPE_HINT = 'type_hint'
    WHITESPACE = 'whitespace'
    ERROR = 'error'
    EOF = 'eof'
    INDENT = 'indent'
    DEDENT = 'dedent'
    NEWLINE = 'newline'

@dataclass
class Position:
    """Represents a position in the source code"""
    line: int
    column: int
    index: int

@dataclass
class Token:
    """Represents a token in the source code"""
    type: TokenType
    value: str
    position: Position

    def __str__(self):
        """Colored string representation of the token"""
        color_map = {
            TokenType.KEYWORD: Fore.BLUE,
            TokenType.IDENTIFIER: Fore.GREEN,
            TokenType.STRING: Fore.YELLOW,
            TokenType.NUMBER: Fore.MAGENTA,
            TokenType.OPERATOR: Fore.RED,
            TokenType.DELIMITER: Fore.WHITE,
            TokenType.COMMENT: Fore.CYAN,
            TokenType.DECORATOR: Fore.MAGENTA,
            TokenType.TYPE_HINT: Fore.CYAN,
            TokenType.ERROR: Fore.RED
        }
        color = color_map.get(self.type, Fore.WHITE)
        return f"{color}{self.value}{Style.RESET_ALL}"

class LexicalError(Exception):
    """Custom exception for lexical errors"""
    def __init__(self, message: str, position: Position):
        self.message = message
        self.position = position
        super().__init__(f"Lexical Error at line {position.line}, column {position.column}: {message}")

class LexicalAnalyzer:
    """Advanced Lexical Analyzer with Enhanced Python Syntax Support"""
    
    # Actualizar las constantes al inicio de la clase
    KEYWORDS = {'def', 'return', 'if', 'else', 'while', 'for', 'in', 'True', 'False', 'None', 'class'}
    TYPE_HINTS = {'int', 'str', 'float', 'bool', 'list', 'dict', 'tuple', 'set'}
    OPERATORS = {
        # Operadores aritméticos
        '+', '-', '*', '/', '//', '%', '**',
        # Operadores de comparación
        '==', '!=', '<', '>', '<=', '>=',
        # Operadores lógicos
        'and', 'or', 'not',
        # Operadores de asignación
        '=', '+=', '-=', '*=', '/=', '//=', '%=',
        # Operadores bit a bit
        '&', '|', '^', '~', '<<', '>>',
        # Operadores especiales
        '->', '=>', ':=',  # Añadimos la flecha para type hints
    }
    TYPO_DICTIONARY = {
        # Errores comunes en inglés
        'pritn': 'print',
        'lenght': 'length',
        'defien': 'define',
        'retrun': 'return',
        'functoin': 'function',
        'whiel': 'while',
        'ture': 'True',
        'flase': 'False',
        'improt': 'import',
        'fro': 'for',
        'fi': 'if',
        'esle': 'else',
        'rnage': 'range',
        'calss': 'class',
        'dfe': 'def',
        'slef': 'self',
        'yeild': 'yield',
        'finaly': 'finally',
        'excpet': 'except',
        'raisee': 'raise',
        'contineu': 'continue',
        'brak': 'break',
        'imoprt': 'import',
        'wirte': 'write',
        'raed': 'read',
        'appned': 'append',
        'inster': 'insert',
        'remvoe': 'remove',
        'dictonary': 'dictionary',
        'lisst': 'list',
        'sett': 'set',
        'touple': 'tuple',
        'booleen': 'boolean',
        'intger': 'integer',
        'floot': 'float',
        'strig': 'string',
        'globel': 'global',
        'locla': 'local',
        'nonlocla': 'nonlocal',
        'lamda': 'lambda',
        'asert': 'assert',
        'delte': 'delete',
        'tyr': 'try',
        'wiht': 'with',
        'yiled': 'yield',
        'passs': 'pass',
        'contniue': 'continue',
        'imprt': 'import',
        'fromm': 'from',
        'ass': 'as',
        'iff': 'if',
        'eliif': 'elif',
        'ellse': 'else',
        'whille': 'while',
        'forr': 'for',
        'inn': 'in',
        'iss': 'is',
        'nott': 'not',
        'andd': 'and',
        'orr': 'or',
        
        # Errores comunes en español
        'imprimir': 'print',
        'si': 'if',
        'sino': 'else',
        'para': 'for',
        'mientras': 'while',
        'retornar': 'return',
        'definir': 'def',
        'clase': 'class',
        'verdadero': 'True',
        'falso': 'False',
        'importar': 'import',
        'rango': 'range',
        'escribir': 'write',
        'leer': 'read',
        'funcion': 'function',
        'variable': 'var',
        'entero': 'int',
        'flotante': 'float',
        'cadena': 'string',
        'booleano': 'bool',
        'lista': 'list',
        'diccionario': 'dict',
        'tupla': 'tuple',
        'conjunto': 'set',
        'nulo': 'None',
        'intentar': 'try',
        'excepto': 'except',
        'finalmente': 'finally',
        'con': 'with',
        'como': 'as',
        'desde': 'from',
        'continuar': 'continue',
        'romper': 'break',
        'pasar': 'pass',
        'global': 'global',
        'local': 'local',
        'nolocal': 'nonlocal',
        'lambda': 'lambda',
        'afirmar': 'assert',
        'eliminar': 'del',
        'producir': 'yield',
        'retorno': 'return',
        'imprima': 'print',
        'defina': 'def',
        'retorne': 'return'
    }

    def __init__(self):
        self.source_code = ""
        self.tokens = []
        self.errors = []
        self.indent_stack = [0]  # Para rastrear niveles de indentación
        
    def handle_indentation(self, line: str, line_number: int) -> int:
        """
        Maneja la indentación al inicio de una línea
        Retorna el número de espacios de indentación
        """
        indent = len(line) - len(line.lstrip())
        if indent % 4 != 0:  # Python usa 4 espacios por nivel
            self._add_error(
                f"Indentación inválida: {indent} espacios (debe ser múltiplo de 4)",
                Position(line_number, 1, 0)
            )
        return indent

    def tokenize(self, source_code: str) -> List[Token]:
        self.source_code = source_code
        self.tokens = []
        self.errors = []
        current_pos = Position(1, 1, 0)
        
        lines = source_code.split('\n')
        for line_num, line in enumerate(lines, 1):
            # Procesar indentación
            if line.strip():
                indent = self.handle_indentation(line, line_num)
                if indent > self.indent_stack[-1]:
                    self.indent_stack.append(indent)
                    self.tokens.append(Token(TokenType.INDENT, " " * indent, current_pos))
                elif indent < self.indent_stack[-1]:
                    while indent < self.indent_stack[-1]:
                        self.indent_stack.pop()
                        self.tokens.append(Token(TokenType.DEDENT, "", current_pos))
                    if indent != self.indent_stack[-1]:
                        self._add_error(
                            f"Indentación inconsistente",
                            Position(line_num, 1, 0)
                        )

            # Procesar el contenido de la línea
            i = indent
            while i < len(line):
                char = line[i]
                
                # Saltar espacios en blanco
                if char.isspace():
                    i += 1
                    continue
                
                # Procesar comentarios
                if char == '#':
                    comment = line[i:]
                    self.tokens.append(Token(TokenType.COMMENT, comment, 
                        Position(line_num, i + 1, current_pos.index + i)))
                    break
                
                # Procesar strings
                if char in '"\'':
                    string_start = i
                    quote = char
                    i += 1
                    while i < len(line) and line[i] != quote:
                        if line[i] == '\\':
                            i += 2
                        else:
                            i += 1
                    if i >= len(line):
                        self._add_error("String sin terminar", 
                            Position(line_num, string_start + 1, current_pos.index + string_start))
                    else:
                        self.tokens.append(Token(TokenType.STRING, line[string_start:i+1], 
                            Position(line_num, string_start + 1, current_pos.index + string_start)))
                        i += 1
                    continue
                
                # Procesar números
                if char.isdigit():
                    num_start = i
                    while i < len(line) and (line[i].isdigit() or line[i] == '.'):
                        i += 1
                    self.tokens.append(Token(TokenType.NUMBER, line[num_start:i], 
                        Position(line_num, num_start + 1, current_pos.index + num_start)))
                    continue
                
                # Procesar identificadores y palabras clave
                if char.isalpha() or char == '_':
                    id_start = i
                    while i < len(line) and (line[i].isalnum() or line[i] == '_'):
                        i += 1
                    word = line[id_start:i]
                    
                    # Verificar si es una palabra clave
                    if word in self.KEYWORDS:
                        self.tokens.append(Token(TokenType.KEYWORD, word, 
                            Position(line_num, id_start + 1, current_pos.index + id_start)))
                    # Verificar si es un type hint
                    elif word in self.TYPE_HINTS:
                        self.tokens.append(Token(TokenType.TYPE_HINT, word, 
                            Position(line_num, id_start + 1, current_pos.index + id_start)))
                    # Es un identificador
                    else:
                        if word in self.TYPO_DICTIONARY:
                            self._add_error(
                                f"Posible error tipográfico: '{word}'. ¿Quisiste decir '{self.TYPO_DICTIONARY[word]}'?",
                                Position(line_num, id_start + 1, current_pos.index + id_start)
                            )
                        self.tokens.append(Token(TokenType.IDENTIFIER, word, 
                            Position(line_num, id_start + 1, current_pos.index + id_start)))
                    continue
                
                # Procesar operadores y delimitadores
                if char in '+-*/%=<>!&|^~':
                    # Verificar operadores de dos caracteres
                    if i + 1 < len(line) and line[i:i+2] in self.OPERATORS:
                        self.tokens.append(Token(TokenType.OPERATOR, line[i:i+2], 
                            Position(line_num, i + 1, current_pos.index + i)))
                        i += 2
                    else:
                        self.tokens.append(Token(TokenType.OPERATOR, char, 
                            Position(line_num, i + 1, current_pos.index + i)))
                        i += 1
                    continue
                
                # Procesar delimitadores
                if char in '(){}[],:;.':
                    self.tokens.append(Token(TokenType.DELIMITER, char, 
                        Position(line_num, i + 1, current_pos.index + i)))
                    i += 1
                    continue
                
                # Carácter no reconocido
                self._add_error(f"Carácter no reconocido: '{char}'", 
                    Position(line_num, i + 1, current_pos.index + i))
                i += 1
            
            # Agregar token de nueva línea al final de cada línea
            self.tokens.append(Token(TokenType.NEWLINE, '\n', 
                Position(line_num, len(line) + 1, current_pos.index + len(line))))
            current_pos = Position(line_num + 1, 1, current_pos.index + len(line) + 1)
        
        # Agregar DEDENT tokens al final si es necesario
        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            self.tokens.append(Token(TokenType.DEDENT, "", current_pos))
        
        # Agregar token EOF
        self.tokens.append(Token(TokenType.EOF, "", current_pos))
        
        return self.tokens
    
    def _add_error(self, message: str, position: Position):
        """Add a lexical error"""
        # Traducir mensajes comunes al español
        if message.startswith("Unrecognized character"):
            char = message.split("'")[1]
            message = f"Carácter no reconocido: '{char}'"
        elif message.startswith("Unterminated string literal"):
            message = "Cadena de texto sin terminar"
        elif message.startswith("Unterminated f-string"):
            message = "f-string sin terminar"
        elif message.startswith("Expected string delimiter"):
            char = message.split("'")[3]
            message = f"Se esperaba un delimitador de cadena después de 'f', se encontró '{char}'"
        elif message.startswith("Possible typo"):
            parts = message.split("'")
            if len(parts) >= 4:
                word = parts[1]
                suggestion = parts[3]
                message = f"Posible error tipográfico: '{word}'. ¿Quisiste decir '{suggestion}'?"
        
        error = {
            'message': message,
            'line': position.line,
            'column': position.column
        }
        self.errors.append(error)
        
    def print_tokens(self):
        """Print all tokens with color"""
        print(f"{Fore.CYAN}🔍 Tokens Encontrados:{Style.RESET_ALL}")
        for token in self.tokens:
            print(f"{token} [{token.type.value}]")
    
    def print_errors(self):
        """Print lexical errors"""
        if self.errors:
            print(f"\n{Fore.RED}❌ Errores Léxicos:{Style.RESET_ALL}")
            for error in self.errors:
                print(f"Línea {error['line']}, Columna {error['column']}: {error['message']}")
        else:
            print(f"\n{Fore.GREEN}✅ No se encontraron errores léxicos{Style.RESET_ALL}")
