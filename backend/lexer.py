import ply.lex as lex
import enum
from dataclasses import dataclass
from typing import List, Optional, Dict
from colorama import init, Fore, Style

# Inicializa colorama para salida coloreada
init()

class TokenType(enum.Enum):
    """Tipos de tokens soportados"""
    KEYWORD = 'keyword'
    IDENTIFIER = 'identifier'
    NUMBER = 'number'
    STRING = 'string'
    OPERATOR = 'operator'
    DELIMITER = 'delimiter'
    COMMENT = 'comment'
    NEWLINE = 'newline'
    ERROR = 'error'
    TYPE_HINT = 'type_hint'
    TEMPLATE_STRING = 'template_string'
    DECORATOR = 'decorator'
    ARROW = 'arrow'
    ASYNC = 'async'
    INDENT = 'indent'
    DEDENT = 'dedent'
    WHITESPACE = 'whitespace'
    EOF = 'eof'
    SIMPLE_STRING = 'simple_string'

@dataclass
class Position:
    """Posición de un token en el código fuente"""
    line: int
    column: int
    index: int = 0  # Posición absoluta en el archivo (opcional)
    filename: str = ""  # Nombre del archivo (opcional)

    def __str__(self):
        return f"{self.filename}:{self.line}:{self.column}" if self.filename else f"{self.line}:{self.column}"

@dataclass
class Token:
    """Representa un token en el código fuente"""
    type: TokenType
    value: str
    position: Position
    error_message: Optional[str] = None

    def __str__(self):
        """Representación del token con color"""
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
            TokenType.ERROR: Fore.RED,
            TokenType.ARROW: Fore.RED,
            TokenType.TEMPLATE_STRING: Fore.YELLOW,
            TokenType.ASYNC: Fore.BLUE,
            TokenType.SIMPLE_STRING: Fore.YELLOW
        }
        color = color_map.get(self.type, Fore.WHITE)
        base = f"{color}{self.value}{Style.RESET_ALL}"
        if self.error_message:
            return f"{base} {Fore.RED}// Error: {self.error_message}{Style.RESET_ALL}"
        return base

class LexicalError(Exception):
    """Excepción para errores léxicos"""
    def __init__(self, message: str, position: Position):
        self.message = message
        self.position = position
        super().__init__(f"{message} at {position}")

class LexicalAnalyzer:
    """Analizador léxico usando PLY"""

    # Lista de tokens para PLY
    tokens = (
        'KEYWORD',
        'IDENTIFIER',
        'STRING',
        'NUMBER',
        'OPERATOR',
        'DELIMITER',
        'COMMENT',
        'DECORATOR',
        'TYPE_HINT',
        'WHITESPACE',
        'ERROR',
        'EOF',
        'INDENT',
        'DEDENT',
        'NEWLINE',
        'ARROW',
        'TEMPLATE_STRING',
        'ASYNC',
        'SIMPLE_STRING'
    )

    # Palabras reservadas
    keywords = {
        'break', 'case', 'catch', 'class', 'const', 'continue', 'debugger',
        'default', 'delete', 'do', 'else', 'enum', 'export', 'extends',
        'false', 'finally', 'for', 'function', 'if', 'import', 'in',
        'instanceof', 'new', 'null', 'return', 'super', 'switch', 'this',
        'throw', 'true', 'try', 'typeof', 'var', 'void', 'while', 'with',
        'as', 'implements', 'interface', 'let', 'package', 'private',
        'protected', 'public', 'static', 'yield', 'any', 'boolean', 'constructor',
        'declare', 'get', 'module', 'require', 'set', 'symbol', 'type',
        'from', 'of', 'async', 'await',
        'def', 'return', 'if', 'else', 'elif', 'while', 'for', 'in', 'True', 'False', 'None',
        'interface', 'type', 'enum', 'implements', 'extends', 'private', 'public', 'protected', 'readonly',
        'pass', 'break', 'continue'
    }

    # Tipos soportados
    type_hints = {
        # Python types
        'int', 'str', 'float', 'bool', 'list', 'dict', 'tuple', 'set',
        # TypeScript types
        'number', 'string', 'boolean', 'any', 'void', 'never', 'object',
        'Array', 'Record', 'Partial', 'Required', 'Pick', 'Omit',
        # Additional TypeScript types
        'undefined', 'null', 'unknown', 'bigint', 'symbol',
        'Promise', 'Map', 'Set', 'Date', 'RegExp'
    }

    # Operadores válidos
    valid_operators = {
        '=',  # Asignación simple
        '+', '-', '*', '/', '%',  # Aritméticos básicos
        '+=', '-=', '*=', '/=', '%=',  # Asignación compuesta
        '==', '!=', '<', '<=', '>', '>=',  # Comparación
        '**', '//',  # Potencia y división entera
        '??', '?.',  # Operadores de TypeScript
        '!.',  # Operador de no-nulo TypeScript
        '->'  # Operador de tipo de retorno Python
    }

    # Reglas de tokens simples
    t_DELIMITER = r'[(){}\[\],.:;?@]'
    t_ignore = ' \t\r'

    def __init__(self, filename: Optional[str] = None):
        self.lexer = None
        self.tokens_list = []
        self.errors = []
        self.filename = filename
        self.indent_stack = [0]  # Para manejar indentación
        self.current_line = 1
        self.current_column = 1
        # Inicializa el lexer
        self.lexer = lex.lex(module=self)

    def find_column(self, token):
        """
        Encuentra la columna donde comienza el token.
        Cuenta los caracteres desde el último salto de línea.
        """
        last_cr = self.lexer.lexdata.rfind('\n', 0, token.lexpos)
        if last_cr < 0:
            last_cr = 0
        column = (token.lexpos - last_cr)
        return column

    def get_position(self, token) -> Position:
        """Obtiene la posición (línea, columna) de un token"""
        return Position(
            line=token.lineno,
            column=self.find_column(token),
            index=token.lexpos,
            filename=self.filename
        )

    def tokenize(self, source_code: str) -> List[Token]:
        """Tokeniza el código fuente usando PLY"""
        self.tokens_list = []
        self.errors = []
        self.lexer.input(source_code)
        
        # Lista de palabras clave y tipos válidos
        valid_keywords = ['def', 'return', 'if', 'else', 'while', 'for', 'in', 'print', 'class', 'pass', 'break', 'continue']
        valid_types = ['int', 'float', 'str', 'bool', 'list', 'dict', 'tuple', 'set']
        
        # Lista de palabras comunes que no son palabras clave
        common_identifiers = {'main', 'base', 'altura', 'area', 'valor', 'resultado', 'nombre', 'suma', 'resta', 'total'}
        
        # Estados para validación
        in_params = False
        param_tokens = []
        current_param = []
        expect_param_type = False
        expect_function_colon = False
        after_return_type = False
        last_param_token = None  # Para validar comas entre parámetros
        
        while True:
            tok = self.lexer.token()
            if not tok:
                break

            # Crear token con posición
            token = Token(
                type=TokenType(tok.type.lower()),
                value=tok.value,
                position=self.get_position(tok)
            )
            
            # Validar palabras clave y tipos mal escritos
            if token.type == TokenType.IDENTIFIER:
                word = token.value.lower()
                # Solo buscar palabras clave similares si:
                # 1. La palabra se parece a una palabra clave (máx 2 cambios)
                # 2. No es un identificador común
                # 3. No está en una posición donde se espera un identificador
                if word not in common_identifiers and not in_params:
                    similar_keyword = self._find_similar_word(word, valid_keywords)
                    if similar_keyword and similar_keyword.lower() != word:
                        error = LexicalError(
                            f"'{token.value}' no es una palabra clave válida. ¿Quisiste decir '{similar_keyword}'?",
                            token.position
                        )
                        self.errors.append(error)
                
                # Validar tipos solo después de : en parámetros o tipo de retorno
                if (in_params and last_param_token and last_param_token.value == ':') or \
                   (after_return_type and token.type == TokenType.IDENTIFIER):
                    similar_type = self._find_similar_word(word, valid_types)
                    if similar_type and similar_type.lower() != word:
                        error = LexicalError(
                            f"'{token.value}' no es un tipo válido. ¿Quisiste decir '{similar_type}'?",
                            token.position
                        )
                        self.errors.append(error)
            
            # Validación de parámetros de función
            if token.value == '(':
                in_params = True
                param_tokens = []
                current_param = []
                expect_param_type = False
                last_param_token = None
            elif token.value == ')':
                in_params = False
                if current_param:
                    param_tokens.append(current_param)
            elif in_params:
                if token.type in [TokenType.COMMENT, TokenType.NEWLINE]:
                    continue
                
                if token.value == ',':
                    if current_param:
                        param_tokens.append(current_param)
                        current_param = []
                        expect_param_type = False
                    last_param_token = None
                else:
                    # Validar comas entre parámetros
                    if token.type == TokenType.IDENTIFIER:
                        if last_param_token and last_param_token.type == TokenType.TYPE_HINT:
                            error = LexicalError(
                                "Falta una coma entre parámetros",
                                token.position
                            )
                            self.errors.append(error)
                    
                    current_param.append(token)
                    last_param_token = token

            # Validación de definición de función
            if token.type == TokenType.KEYWORD and token.value == 'def':
                expect_function_colon = True
            elif expect_function_colon:
                if token.type == TokenType.OPERATOR and token.value == '->':
                    after_return_type = True
                elif after_return_type and token.type == TokenType.TYPE_HINT:
                    # Después del tipo de retorno, debe venir un :
                    next_token = self.lexer.token()
                    if not next_token or next_token.type.lower() != 'delimiter' or next_token.value != ':':
                        error = LexicalError(
                            "Falta el ':' después de la definición de función",
                            token.position
                        )
                        self.errors.append(error)
                    else:
                        # No olvidar procesar el token que acabamos de consumir
                        self.tokens_list.append(Token(
                            type=TokenType(next_token.type.lower()),
                            value=next_token.value,
                            position=self.get_position(next_token)
                        ))
                    expect_function_colon = False
                    after_return_type = False
                elif token.type == TokenType.NEWLINE:
                    expect_function_colon = False
                    after_return_type = False
            
            self.tokens_list.append(token)
            
        return self.tokens_list

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calcula la distancia de Levenshtein entre dos strings"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]

    def _find_similar_word(self, word: str, valid_words: list) -> str:
        """Encuentra la palabra más similar de una lista de palabras válidas"""
        min_distance = float('inf')
        similar_word = None
        
        for valid_word in valid_words:
            distance = self._levenshtein_distance(word.lower(), valid_word.lower())
            if distance < min_distance and distance <= 2:  # máximo 2 cambios
                min_distance = distance
                similar_word = valid_word
        
        return similar_word

    def _validate_parameters(self, param_tokens):
        """Valida la sintaxis de los parámetros de función"""
        for i, param in enumerate(param_tokens):
            # Verificar que cada parámetro tenga la forma correcta (identificador: tipo)
            if len(param) >= 2:
                if not (param[0].type == TokenType.IDENTIFIER and 
                       param[1].type == TokenType.DELIMITER and 
                       param[1].value == ':'):
                    error = LexicalError(
                        "Parámetro mal formado",
                        param[0].position
                    )
                    self.errors.append(error)

    def t_OPERATOR(self, t):
        r'->|=|[+\-*/%]=?|==|!=|<=?|>=?|\*\*|\/\/|\?\?|\?\.|\!\.'
        if t.value not in self.valid_operators:
            error = LexicalError(f"Operador inválido '{t.value}'", self.get_position(t))
            self.errors.append(error)
            t.type = 'ERROR'
        return t

    def t_error(self, t):
        """Manejo de caracteres ilegales"""
        # Caracteres especiales no permitidos
        special_chars = {'!', '@', '#', '$', '%', '^', '&', '~'}
        if t.value[0] in special_chars:
            error = LexicalError(f"Caracter especial no permitido '{t.value[0]}'", self.get_position(t))
            self.errors.append(error)
        elif not self._is_valid_unicode(t.value[0]):
            error = LexicalError(f"Caracter ilegal '{t.value[0]}'", self.get_position(t))
            self.errors.append(error)
        t.type = 'ERROR'
        t.value = t.value[0]
        t.lexer.skip(1)
        return t

    def t_ARROW(self, t):
        r'->'
        return t

    def t_TEMPLATE_STRING(self, t):
        r'f"[^"]*"|f\'[^\']*\''
        t.value = t.value[2:-1]  # Remover f y comillas
        return t

    def t_DECORATOR(self, t):
        r'@[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*(\([^)]*\))?'
        return t

    def t_IDENTIFIER(self, t):
        r'[a-zA-Z_\u00C0-\u00FF][a-zA-Z0-9_\u00C0-\u00FF]*'
        # Verificar si es una palabra clave
        if t.value in self.keywords:
            t.type = 'KEYWORD'
        # Verificar si es un tipo
        elif t.value in self.type_hints:
            t.type = 'TYPE_HINT'
        # Verificar si es async/await
        elif t.value in ['async', 'await']:
            t.type = 'ASYNC'
        return t

    def t_NUMBER(self, t):
        r'\d*\.\d+|\d+'
        try:
            float(t.value)  # Valida que sea un número válido
            return t
        except ValueError:
            error = LexicalError(f"Número inválido: {t.value}", self.get_position(t))
            self.errors.append(error)
            t.type = 'ERROR'
            return t

    def t_STRING(self, t):
        r'\"\"\"[\s\S]*?\"\"\"|\'\'\'[\s\S]*?\'\'\'|"[^"]*"|\'[^\']*\''
        # Detectar si es un docstring (comentario multilinea)
        if t.value.startswith('"""') or t.value.startswith("'''"):
            t.type = 'COMMENT'
            # Preservar el formato del docstring
            t.value = t.value.strip('"""').strip("'''").strip()
        else:
            # String normal
            t.value = t.value[1:-1]  # Remover comillas
        return t

    def t_SIMPLE_STRING(self, t):
        r'"[^"]*"|\'[^\']*\''
        t.value = t.value[1:-1]  # Remover comillas
        t.type = 'SIMPLE_STRING'
        return t

    def t_COMMENT(self, t):
        r'[#].*|//.*'  # Soporta comentarios de Python (#) y TypeScript (//)
        t.value = t.value.strip()
        return t

    def t_newline(self, t):
        r'\n+'
        t.type = 'NEWLINE'
        t.lexer.lineno += len(t.value)
        return t

    def print_tokens(self, show_position: bool = True):
        """Imprime todos los tokens con color y opcionalmente su posición"""
        print(f"\n{Fore.CYAN}🔍 Análisis Léxico{Style.RESET_ALL}")
        print("=" * 80)
        
        # Agrupar tokens por línea
        tokens_by_line = {}
        for token in self.tokens_list:
            line = token.position.line
            if line not in tokens_by_line:
                tokens_by_line[line] = []
            tokens_by_line[line].append(token)
        
        # Imprimir tokens organizados por línea
        print(f"{Fore.CYAN}Tokens encontrados por línea:{Style.RESET_ALL}")
        for line in sorted(tokens_by_line.keys()):
            print(f"\n{Fore.YELLOW}Línea {line}:{Style.RESET_ALL}")
            for token in tokens_by_line[line]:
                token_info = f"  {token.type.value:12} │ {token.value}"
                if show_position:
                    token_info += f" @ columna {token.position.column}"
                print(token_info)
    
    def print_errors(self):
        """Imprime errores léxicos organizados"""
        if self.errors:
            print(f"\n{Fore.RED}❌ Errores Léxicos Encontrados:{Style.RESET_ALL}")
            print("=" * 80)
            
            # Agrupar errores por línea
            errors_by_line = {}
            for error in self.errors:
                if isinstance(error, LexicalError):
                    line = error.position.line
                    if line not in errors_by_line:
                        errors_by_line[line] = []
                    errors_by_line[line].append(error)
                else:
                    # Para errores que no son LexicalError
                    if 0 not in errors_by_line:
                        errors_by_line[0] = []
                    errors_by_line[0].append(error)
            
            # Imprimir errores organizados por línea
            for line in sorted(errors_by_line.keys()):
                if line == 0:
                    print(f"\n{Fore.RED}Errores generales:{Style.RESET_ALL}")
                else:
                    print(f"\n{Fore.RED}Línea {line}:{Style.RESET_ALL}")
                
                for error in errors_by_line[line]:
                    if isinstance(error, LexicalError):
                        print(f"  • {error.message}")
                        print(f"    └─ Columna {error.position.column}")
                    else:
                        print(f"  • {str(error)}")
        else:
            print(f"\n{Fore.GREEN}✅ No se encontraron errores léxicos{Style.RESET_ALL}")
            print("=" * 80)

    def _is_valid_unicode(self, char):
        """Verifica si un caracter es Unicode válido para identificadores"""
        # Permitir letras Unicode en el rango Latin-1 Supplement
        if '\u00C0' <= char <= '\u00FF':
            return True
        # Permitir caracteres ASCII básicos
        if ord(char) < 128:
            return True
        return False
