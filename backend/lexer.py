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
        self.tokens: List[Token] = []
        self.errors: List[dict] = []
        
    def tokenize(self, source_code: str) -> List[Token]:
        """Main tokenization method"""
        self.source_code = source_code
        self.tokens = []
        self.errors = []
        
        current_pos = Position(1, 1, 0)
        current_lexeme = ""
        state = 'START'
        string_start_pos = None
        
        while current_pos.index < len(source_code):
            char = source_code[current_pos.index]
            
            if state == 'START':
                if char.isspace():
                    if char == '\n':
                        current_pos = Position(current_pos.line + 1, 1, current_pos.index + 1)
                    else:
                        current_pos = Position(current_pos.line, current_pos.column + 1, current_pos.index + 1)
                    continue
                
                elif char == '@':
                    state = 'DECORATOR'
                    current_lexeme = char
                    current_pos = Position(current_pos.line, current_pos.column + 1, current_pos.index + 1)
                
                elif char.isalpha() or char == '_':
                    # Verificar si es una f-string
                    if char == 'f' and current_pos.index + 1 < len(source_code) and source_code[current_pos.index + 1] in ['"', "'"]:
                        # Es una f-string, procesarla como un string
                        string_start_pos = current_pos
                        current_lexeme = char
                        current_pos = Position(current_pos.line, current_pos.column + 1, current_pos.index + 1)
                        state = 'F_STRING'
                    else:
                        # Es un identificador normal
                        state = 'IDENTIFIER'
                        current_lexeme = char
                        current_pos = Position(current_pos.line, current_pos.column + 1, current_pos.index + 1)
                
                elif char.isdigit():
                    state = 'NUMBER'
                    current_lexeme = char
                    current_pos = Position(current_pos.line, current_pos.column + 1, current_pos.index + 1)
                
                elif char in ['"', "'"]:
                    state = 'STRING'
                    string_start_pos = current_pos
                    current_lexeme = char
                    current_pos = Position(current_pos.line, current_pos.column + 1, current_pos.index + 1)
                
                elif char == '#':
                    state = 'COMMENT'
                    current_lexeme = char
                    current_pos = Position(current_pos.line, current_pos.column + 1, current_pos.index + 1)
                
                elif char in '+-*/=<>!&|^~':
                    # Verificar operadores de dos caracteres
                    if current_pos.index + 1 < len(source_code):
                        next_char = source_code[current_pos.index + 1]
                        two_char_op = char + next_char
                        if two_char_op in self.OPERATORS:
                            self.tokens.append(Token(TokenType.OPERATOR, two_char_op, current_pos))
                            current_pos = Position(
                                current_pos.line,
                                current_pos.column + 2,
                                current_pos.index + 2
                            )
                            continue
                    
                    # Si no es un operador de dos caracteres, procesar como uno solo
                    self.tokens.append(Token(TokenType.OPERATOR, char, current_pos))
                    current_pos = Position(
                        current_pos.line,
                        current_pos.column + 1,
                        current_pos.index + 1
                    )
                
                elif char in '(){}[],:;.':
                    self.tokens.append(Token(TokenType.DELIMITER, char, current_pos))
                    current_pos = Position(current_pos.line, current_pos.column + 1, current_pos.index + 1)
                
                else:
                    self._add_error(f"Unrecognized character: '{char}'", current_pos)
                    current_pos = Position(current_pos.line, current_pos.column + 1, current_pos.index + 1)
            
            elif state == 'DECORATOR':
                if char.isalnum() or char == '_':
                    current_lexeme += char
                    current_pos = Position(current_pos.line, current_pos.column + 1, current_pos.index + 1)
                else:
                    self.tokens.append(Token(TokenType.DECORATOR, current_lexeme, current_pos))
                    state = 'START'
                    current_lexeme = ""
            
            elif state == 'IDENTIFIER':
                if char.isalnum() or char == '_':
                    current_lexeme += char
                    current_pos = Position(current_pos.line, current_pos.column + 1, current_pos.index + 1)
                else:
                    token_type = TokenType.KEYWORD if current_lexeme in self.KEYWORDS else TokenType.IDENTIFIER
                    if current_lexeme in self.TYPE_HINTS:
                        token_type = TokenType.TYPE_HINT
                    if current_lexeme in self.TYPO_DICTIONARY:
                        self._add_error(
                            f"Possible typo: '{current_lexeme}'. Did you mean '{self.TYPO_DICTIONARY[current_lexeme]}'?",
                            Position(current_pos.line, current_pos.column - len(current_lexeme), current_pos.index - len(current_lexeme))
                        )
                    self.tokens.append(Token(token_type, current_lexeme, current_pos))
                    state = 'START'
                    current_lexeme = ""
            
            elif state == 'NUMBER':
                if char.isdigit() or char == '.':
                    current_lexeme += char
                    current_pos = Position(current_pos.line, current_pos.column + 1, current_pos.index + 1)
                else:
                    self.tokens.append(Token(TokenType.NUMBER, current_lexeme, current_pos))
                    state = 'START'
                    current_lexeme = ""
            
            elif state == 'F_STRING':
                # Obtener el delimitador de la cadena (comilla simple o doble)
                quote = source_code[current_pos.index]
                if quote not in ['"', "'"]:
                    self._add_error(f"Expected string delimiter after 'f', got '{quote}'", current_pos)
                    state = 'START'
                    continue
                
                current_lexeme += quote
                current_pos = Position(current_pos.line, current_pos.column + 1, current_pos.index + 1)
                
                # Procesar el contenido de la f-string
                while current_pos.index < len(source_code):
                    char = source_code[current_pos.index]
                    current_lexeme += char
                    current_pos = Position(current_pos.line, current_pos.column + 1, current_pos.index + 1)
                    
                    if char == quote and current_lexeme[-2] != '\\':  # Verificar que no sea una comilla escapada
                        # Fin de la f-string
                        self.tokens.append(Token(TokenType.STRING, current_lexeme, string_start_pos))
                        state = 'START'
                        current_lexeme = ""
                        break
                    
                    if char == '\n':
                        self._add_error("Unterminated f-string", string_start_pos)
                        state = 'START'
                        current_lexeme = ""
                        current_pos = Position(current_pos.line + 1, 1, current_pos.index)
                        break
                
                # Si llegamos al final del archivo sin cerrar la cadena
                if current_pos.index >= len(source_code) and state == 'F_STRING':
                    self._add_error("Unterminated f-string", string_start_pos)
                    state = 'START'
                    current_lexeme = ""
            
            elif state == 'STRING':
                quote = current_lexeme[0]  # El primer carácter es la comilla que abre
                current_lexeme += char
                current_pos = Position(current_pos.line, current_pos.column + 1, current_pos.index + 1)
                
                if char == quote and current_lexeme[-2] != '\\':  # Verificar que no sea una comilla escapada
                    # Fin de la cadena
                    self.tokens.append(Token(TokenType.STRING, current_lexeme, string_start_pos))
                    state = 'START'
                    current_lexeme = ""
                elif char == '\n':
                    self._add_error("Unterminated string literal", string_start_pos)
                    state = 'START'
                    current_lexeme = ""
                    current_pos = Position(current_pos.line + 1, 1, current_pos.index)
            
            elif state == 'COMMENT':
                if char == '\n':
                    self.tokens.append(Token(TokenType.COMMENT, current_lexeme, current_pos))
                    current_pos = Position(current_pos.line + 1, 1, current_pos.index + 1)
                    state = 'START'
                    current_lexeme = ""
                else:
                    current_lexeme += char
                    current_pos = Position(current_pos.line, current_pos.column + 1, current_pos.index + 1)
        
        # Handle any remaining lexeme
        if current_lexeme:
            if state == 'STRING':
                self._add_error("Unterminated string literal", current_pos)
            elif state == 'COMMENT':
                self.tokens.append(Token(TokenType.COMMENT, current_lexeme, current_pos))
            elif state in ['IDENTIFIER', 'NUMBER', 'OPERATOR']:
                self.tokens.append(Token(TokenType.IDENTIFIER, current_lexeme, current_pos))
        
        # Add EOF token
        self.tokens.append(Token(TokenType.EOF, '', current_pos))
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
