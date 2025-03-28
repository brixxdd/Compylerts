from typing import List, Optional, Any
from dataclasses import dataclass
from lexer import Token, TokenType, LexicalAnalyzer
from ast_nodes import *

class SyntaxError(Exception):
    def __init__(self, message: str, token: Token):
        self.message = message
        self.token = token
        super().__init__(f"Error de sintaxis en línea {token.position.line}, columna {token.position.column}: {message}")

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.current = 0
        self.errors = []
        self.indent_level = 0  # Nivel actual de indentación

    def parse(self):
        """Parse the program and return an AST"""
        try:
            return self.programa()
        except Exception as e:
            self.errors.append(e)
            return None

    def programa(self):
        """
        PROGRAMA → DECLARACIÓN*
        """
        declaraciones = []
        while not self.is_at_end():
            # Ignorar líneas en blanco consecutivas
            while self.check(TokenType.NEWLINE):
                self.advance()
            
            if self.is_at_end():
                break
            
            try:
                decl = self.declaracion()
                if decl:
                    declaraciones.append(decl)
            except SyntaxError as e:
                self.errors.append(e)
                self.synchronize()
        return Program(declaraciones)

    def declaracion(self):
        """
        DECLARACIÓN → DECLARACIÓN_VAR | DECLARACIÓN_FUN | IF_STMT | RETURN_STMT | EXPRESIÓN_STATEMENT
        """
        # Ignorar comentarios
        if self.check(TokenType.COMMENT):
            self.advance()
            return None
        
        # Verificar si es una declaración de función
        if self.match_keyword("def"):
            return self.declaracion_fun()
        
        # Verificar si es una declaración if
        if self.match_keyword("if"):
            return self.if_statement()
        
        # Verificar si es una declaración return
        if self.match_keyword("return"):
            return self.return_statement()
        
        # Verificar si es una declaración de variable
        if self.check(TokenType.IDENTIFIER):
            # Guardar la posición actual para poder retroceder si es necesario
            current_pos = self.current
            
            # Avanzar al siguiente token después del identificador
            self.advance()
            
            # Si el siguiente token es un operador de asignación
            if self.check_token(TokenType.OPERATOR, "="):
                # Retroceder al identificador
                self.current = current_pos
                return self.declaracion_var()
            else:
                # No es una asignación, retroceder y tratar como expresión
                self.current = current_pos
        
        # Si llegamos aquí, debe ser una expresión
        return self.expresion_statement()

    def declaracion_var(self):
        """
        DECLARACIÓN_VAR → IDENTIFICADOR "=" EXPRESIÓN
        """
        nombre = self.consume(TokenType.IDENTIFIER, "Se esperaba un identificador").value
        self.consume(TokenType.OPERATOR, "Se esperaba '=' después del identificador")
        valor = self.expresion()
        return VarDecl(nombre, valor)

    def declaracion_fun(self):
        """
        DECLARACIÓN_FUN → "def" IDENTIFICADOR "(" PARAMS ")" [ "->" TIPO ] ":" BLOQUE
        """
        try:
            nombre = self.consume(TokenType.IDENTIFIER, "Se esperaba nombre de función").value
            self.consume(TokenType.DELIMITER, "Se esperaba '(' después del nombre de función")
            
            parametros = []
            if not self.check_token(TokenType.DELIMITER, ")"):
                parametros = self.params()
            
            # Verificar que se cierre el paréntesis
            self.consume(TokenType.DELIMITER, "Se esperaba ')' después de los parámetros")
            
            # Verificar si hay un type hint para el valor de retorno
            tipo_retorno = None
            if self.match_token(TokenType.OPERATOR, "->"):
                tipo_retorno = self.tipo()
            
            # Verificar los dos puntos después de la declaración de función
            self.consume(TokenType.DELIMITER, "Se esperaba ':' después de la declaración de función")
            
            # Consumir cualquier NEWLINE después de los dos puntos
            while self.check(TokenType.NEWLINE) or self.check(TokenType.COMMENT):
                self.advance()
            
            # Ahora debería haber un token INDENT
            return FunDecl(nombre, parametros, tipo_retorno, self.bloque())
        except SyntaxError as e:
            self.errors.append(e)
            self.synchronize()
            return None

    def params(self):
        """
        PARAMS → [PARAM ("," PARAM)*]
        PARAM → IDENTIFICADOR [":" TIPO]
        """
        parametros = []
        
        # Obtener el primer parámetro
        param_token = self.consume(TokenType.IDENTIFIER, "Se esperaba nombre de parámetro")
        param_name = param_token.value
        
        # Verificar si hay un type hint para este parámetro
        if self.match_token(TokenType.DELIMITER, ":"):
            # Consumir el tipo y descartarlo (no lo usamos en el AST por ahora)
            self.consume(TokenType.TYPE_HINT, "Se esperaba un tipo después de ':'")
        
        parametros.append(param_name)
        
        # Procesar parámetros adicionales
        while self.match_token(TokenType.DELIMITER, ","):
            # Verificar que no haya coma extra antes del cierre
            if self.check_token(TokenType.DELIMITER, ")"):
                raise self.error(self.previous(), "Coma extra antes del cierre de paréntesis")
            
            param_token = self.consume(TokenType.IDENTIFIER, "Se esperaba nombre de parámetro después de ','")
            param_name = param_token.value
            
            # Verificar si hay un type hint para este parámetro
            if self.match_token(TokenType.DELIMITER, ":"):
                # Consumir el tipo y descartarlo (no lo usamos en el AST por ahora)
                self.consume(TokenType.TYPE_HINT, "Se esperaba un tipo después de ':'")
            
            parametros.append(param_name)
        
        return parametros

    def tipo(self):
        """
        TIPO → "int" | "str" | "bool" | "float" | "list" | "dict"
        """
        tipo = self.consume(TokenType.TYPE_HINT, "Se esperaba un tipo válido")
        return tipo.value

    def expresion_statement(self):
        """
        EXPRESIÓN_STATEMENT → EXPRESIÓN
        """
        # Si encontramos un comentario o una línea en blanco, lo ignoramos
        if self.check(TokenType.COMMENT) or self.check(TokenType.NEWLINE):
            self.advance()
            return None
        
        try:
            expr = self.expresion()
            
            # Consumir el token NEWLINE si existe
            if self.check(TokenType.NEWLINE):
                self.advance()
            
            return ExpressionStmt(expr)
        except Exception as e:
            self.errors.append(SyntaxError(f"Error en expresión: {str(e)}", self.peek()))
            self.synchronize()
            return None

    def expresion(self):
        """
        EXPRESIÓN → ASIGNACIÓN
        """
        return self.asignacion()

    def asignacion(self):
        """
        ASIGNACIÓN → COMPARACIÓN ("=" ASIGNACIÓN)?
        """
        expr = self.comparacion()
        
        if self.match_token(TokenType.OPERATOR, "="):
            valor = self.asignacion()
            if isinstance(expr, Identifier):
                return AssignExpr(expr, valor)
            raise self.error(self.previous(), "Objetivo de asignación inválido")
        
        return expr

    def comparacion(self):
        """
        COMPARACIÓN → SUMA (("==" | "!=") SUMA)*
        """
        expr = self.suma()
        
        while self.match_token(TokenType.OPERATOR, "==") or self.match_token(TokenType.OPERATOR, "!="):
            operador = self.previous().value
            derecho = self.suma()
            expr = BinaryExpr(expr, operador, derecho)
        
        return expr

    def suma(self):
        """
        SUMA → MULT (("+" | "-") MULT)*
        """
        expr = self.mult()
        
        while self.match_token(TokenType.OPERATOR, "+") or self.match_token(TokenType.OPERATOR, "-"):
            operador = self.previous().value
            derecho = self.mult()
            expr = BinaryExpr(expr, operador, derecho)
        
        return expr

    def mult(self):
        """
        MULT → UNARIO (("*" | "/" | "//" | "%") UNARIO)*
        """
        expr = self.unario()
        
        while (self.match_token(TokenType.OPERATOR, "*") or 
               self.match_token(TokenType.OPERATOR, "/") or
               self.match_token(TokenType.OPERATOR, "//") or
               self.match_token(TokenType.OPERATOR, "%")):
            operador = self.previous().value
            derecho = self.unario()
            expr = BinaryExpr(expr, operador, derecho)
        
        return expr

    def unario(self):
        """
        UNARIO → ("-" | "!") UNARIO | PRIMARIO
        """
        if self.match_token(TokenType.OPERATOR, "-") or self.match_token(TokenType.OPERATOR, "!"):
            operador = self.previous().value
            derecho = self.unario()
            return UnaryExpr(operador, derecho)
        
        return self.primario()

    def primario(self):
        """
        PRIMARIO → NUMERO | STRING | "True" | "False" | "None" | "(" EXPRESIÓN ")" | IDENTIFICADOR | LLAMADA
        """
        if self.match(TokenType.NUMBER):
            return Literal(float(self.previous().value))
        
        if self.match(TokenType.STRING):
            return Literal(self.previous().value[1:-1])  # Quitar comillas
        
        if self.match_keyword("True"):
            return Literal(True)
        
        if self.match_keyword("False"):
            return Literal(False)
        
        if self.match_keyword("None"):
            return Literal(None)
        
        if self.match_token(TokenType.DELIMITER, "("):
            expr = self.expresion()
            self.consume(TokenType.DELIMITER, "Se esperaba ')' después de la expresión")
            return GroupingExpr(expr)
        
        if self.match(TokenType.IDENTIFIER):
            name = self.previous().value
            
            # Verificar si es una llamada a función
            if self.check_token(TokenType.DELIMITER, "("):
                return self.finalizar_llamada(Identifier(name))
            
            # Verificar si es una f-string (identificador 'f' seguido de una cadena)
            if name == "f" and self.check(TokenType.STRING):
                string_value = self.advance().value
                return Literal(string_value[1:-1])  # Quitar comillas
            
            return Identifier(name)
        
        # Si es una llamada a función con una palabra clave como 'print'
        if self.match(TokenType.KEYWORD) and self.check_token(TokenType.DELIMITER, "("):
            name = self.previous().value
            return self.finalizar_llamada(Identifier(name))
        
        raise self.error(self.peek(), "Se esperaba una expresión")

    def finalizar_llamada(self, callee):
        """Finalizar una llamada a función"""
        arguments = []
        
        # Consumir el paréntesis de apertura
        self.consume(TokenType.DELIMITER, "Se esperaba '(' después del nombre de función")
        
        # Si no hay argumentos
        if not self.check_token(TokenType.DELIMITER, ")"):
            # Procesar el primer argumento
            arguments.append(self.expresion())
            
            # Procesar argumentos adicionales
            while self.match_token(TokenType.DELIMITER, ","):
                arguments.append(self.expresion())
        
        # Consumir el paréntesis de cierre
        self.consume(TokenType.DELIMITER, "Se esperaba ')' después de los argumentos")
        
        return CallExpr(callee, arguments)

    def bloque(self):
        """
        BLOQUE → DECLARACIÓN*
        """
        declaraciones = []
        
        # Verificar que haya un token INDENT después de los dos puntos
        if not self.match(TokenType.INDENT):
            raise self.error(self.peek(), "Se esperaba indentación después de los dos puntos")
        
        # Procesar declaraciones hasta encontrar un DEDENT o EOF
        while not self.is_at_end() and not self.check(TokenType.DEDENT):
            # Ignorar líneas en blanco (solo NEWLINE)
            if self.check(TokenType.NEWLINE):
                self.advance()
                continue
            
            try:
                decl = self.declaracion()
                if decl:
                    declaraciones.append(decl)
            except SyntaxError as e:
                self.errors.append(e)
                self.synchronize()
        
        # Consumir el token DEDENT si existe
        if self.check(TokenType.DEDENT):
            self.advance()
        
        return declaraciones

    def check_indentation(self) -> bool:
        """Verifica que la indentación sea correcta"""
        # Esta función ya no es necesaria con el manejo de tokens INDENT/DEDENT
        return True

    def return_statement(self):
        """
        RETURN_STMT → "return" EXPRESIÓN?
        """
        keyword = self.previous()  # token 'return'
        valor = None
        
        if not self.check_token(TokenType.DELIMITER, ";") and not self.is_at_end():
            valor = self.expresion()
        
        return ReturnStmt(valor)

    def if_statement(self):
        """
        IF_STMT → "if" EXPRESIÓN ":" BLOQUE ("else" ":" BLOQUE)?
        """
        condicion = self.expresion()
        
        if not self.match_token(TokenType.DELIMITER, ":"):
            raise self.error(self.peek(), "Falta ':' después de la condición if")
        
        then_branch = self.bloque()
        
        else_branch = None
        if self.match_keyword("else"):
            if not self.match_token(TokenType.DELIMITER, ":"):
                raise self.error(self.peek(), "Falta ':' después de 'else'")
            else_branch = self.bloque()
        
        return IfStmt(condicion, then_branch, else_branch)

    # Métodos auxiliares
    def match(self, *types: TokenType) -> bool:
        """Check if current token matches any of the given types"""
        for type in types:
            if self.check(type):
                self.advance()
                return True
        return False

    def match_token(self, type: TokenType, value: str = None) -> bool:
        """Match if the current token is of the given type and value"""
        if not self.check(type):
            return False
        
        if value is not None and self.peek().value != value:
            return False
        
        self.advance()
        return True

    def match_keyword(self, keyword: str) -> bool:
        """Match if the current token is a keyword with the given value"""
        if self.check(TokenType.KEYWORD) and self.peek().value == keyword:
            self.advance()
            return True
        return False

    def check(self, type: TokenType) -> bool:
        """Check if current token is of given type"""
        if self.is_at_end():
            return False
        return self.peek().type == type

    def check_token(self, type: TokenType, value: str = None) -> bool:
        """Check if the current token is of the given type and value"""
        if self.is_at_end():
            return False
        
        if self.peek().type != type:
            return False
        
        if value is not None and self.peek().value != value:
            return False
        
        return True

    def check_keyword(self, keyword: str) -> bool:
        """Check if current token is a keyword with the given value"""
        return self.check(TokenType.KEYWORD) and self.peek().value == keyword

    def advance(self) -> Token:
        """Advance to next token"""
        if not self.is_at_end():
            self.current += 1
        return self.previous()

    def consume(self, type: TokenType, message: str) -> Token:
        """Consume the current token if it matches the given type, otherwise throw an error"""
        if self.check(type):
            return self.advance()
        raise self.error(self.peek(), message)

    def error(self, token: Token, message: str) -> SyntaxError:
        """Create a syntax error"""
        # Traducir mensajes comunes
        if message == "Expected argument after comma, got ')'":
            message = "Se esperaba un argumento después de la coma, se encontró ')'"
        elif message == "Invalid assignment target.":
            message = "Objetivo de asignación inválido."
        elif message == "Expect expression.":
            message = "Se esperaba una expresión."
        elif message == "Expect ')' after expression.":
            message = "Se esperaba ')' después de la expresión."
        elif message == "Expect ')' after arguments.":
            message = "Se esperaba ')' después de los argumentos."
        elif message == "Expect ':' after if condition.":
            message = "Se esperaba ':' después de la condición if."
        elif message == "Expect ':' after 'else'.":
            message = "Se esperaba ':' después de 'else'."
        elif message == "Expect ':' after while condition.":
            message = "Se esperaba ':' después de la condición while."
        elif message == "Expect ':' before function body.":
            message = "Se esperaba ':' antes del cuerpo de la función."
        elif message == "Expect '(' after function name.":
            message = "Se esperaba '(' después del nombre de la función."
        elif message == "Expect function name.":
            message = "Se esperaba el nombre de la función."
        elif message == "Expect parameter name.":
            message = "Se esperaba el nombre del parámetro."
        elif message == "Expect type hint after ':'.":
            message = "Se esperaba un tipo después de ':'."
        elif message == "Expect return type after '->'.":
            message = "Se esperaba un tipo de retorno después de '->'."
        elif message.startswith("Expect"):
            message = message.replace("Expect", "Se esperaba")
            
        return SyntaxError(message, token)

    def is_at_end(self) -> bool:
        """Check if we've reached the end of input"""
        return self.peek().type == TokenType.EOF

    def peek(self) -> Token:
        """Return current token"""
        return self.tokens[self.current]

    def previous(self) -> Token:
        """Return previous token"""
        return self.tokens[self.current - 1]

    def synchronize(self):
        """Error recovery - advance to next statement"""
        self.advance()

        while not self.is_at_end():
            # Si encontramos un token de nueva línea, podría ser el final de la declaración actual
            if self.previous().type == TokenType.NEWLINE:
                return

            # Si encontramos un token de indentación o desindentación, estamos en un nuevo bloque
            if self.peek().type in [TokenType.INDENT, TokenType.DEDENT]:
                return

            # Si encontramos una palabra clave que podría iniciar una nueva declaración
            if self.peek().type == TokenType.KEYWORD and self.peek().value in ["def", "class", "if", "while", "for", "return"]:
                return

            self.advance() 

    def check_next(self, type: TokenType, value: str = None) -> bool:
        """Check if the next token is of the given type and value"""
        if self.is_at_end() or self.current + 1 >= len(self.tokens):
            return False
        
        next_token = self.tokens[self.current + 1]
        if next_token.type != type:
            return False
        
        if value is not None and next_token.value != value:
            return False
        
        return True 