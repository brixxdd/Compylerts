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
        'pritn': 'print',
        'lenght': 'length',
        'defien': 'define',
        'retrun': 'return'
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
                    state = 'IDENTIFIER'
                    current_lexeme = char
                    current_pos = Position(current_pos.line, current_pos.column + 1, current_pos.index + 1)
                
                elif char.isdigit():
                    state = 'NUMBER'
                    current_lexeme = char
                    current_pos = Position(current_pos.line, current_pos.column + 1, current_pos.index + 1)
                
                elif char in ['"', "'"]:
                    state = 'STRING'
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
            
            elif state == 'STRING':
                if char == '\n':
                    self._add_error("Unterminated string literal", current_pos)
                    state = 'START'
                    current_lexeme = ""
                    current_pos = Position(current_pos.line + 1, 1, current_pos.index + 1)
                else:
                    current_lexeme += char
                    current_pos = Position(current_pos.line, current_pos.column + 1, current_pos.index + 1)
                    if char == current_lexeme[0] and len(current_lexeme) > 1:
                        self.tokens.append(Token(TokenType.STRING, current_lexeme, current_pos))
                        state = 'START'
                        current_lexeme = ""
            
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
        error = {
            'message': message,
            'line': position.line,
            'column': position.column
        }
        self.errors.append(error)
        
    def print_tokens(self):
        """Print all tokens with color"""
        print(f"{Fore.CYAN}🔍 Tokens Found:{Style.RESET_ALL}")
        for token in self.tokens:
            print(f"{token} [{token.type.value}]")
    
    def print_errors(self):
        """Print lexical errors"""
        if self.errors:
            print(f"\n{Fore.RED}❌ Lexical Errors:{Style.RESET_ALL}")
            for error in self.errors:
                print(f"Line {error['line']}, Column {error['column']}: {error['message']}")
        else:
            print(f"\n{Fore.GREEN}✅ No lexical errors found{Style.RESET_ALL}")
