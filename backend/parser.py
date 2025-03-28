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
        if self.check(TokenType.COMMENT):
            self.advance()
            return None
        
        if self.match(TokenType.IDENTIFIER) and self.check_token(TokenType.OPERATOR, "="):
            return self.declaracion_var()
        
        if self.match_keyword("def"):
            return self.declaracion_fun()
        
        if self.match_keyword("if"):
            return self.if_statement()
        
        if self.match_keyword("return"):
            return self.return_statement()
        
        return self.expresion_statement()

    def declaracion_var(self):
        """
        DECLARACIÓN_VAR → IDENTIFICADOR "=" EXPRESIÓN
        """
        nombre = self.previous().value
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
            parentesis_abiertos = 1  # Contador de paréntesis
            
            if not self.check_token(TokenType.DELIMITER, ")"):
                parametros = self.params()
            
            # Verificar que se cierre el paréntesis
            if not self.match_token(TokenType.DELIMITER, ")"):
                raise self.error(self.peek(), "Paréntesis sin cerrar en la definición de función")
            
            self.consume(TokenType.DELIMITER, "Se esperaba ':' después de la declaración de función")
            return FunDecl(nombre, parametros, None, self.bloque())
        except SyntaxError as e:
            self.errors.append(e)
            self.synchronize()
            return None

    def params(self):
        """
        PARAMS → [IDENTIFICADOR ("," IDENTIFICADOR)*]
        """
        parametros = []
        parametros.append(self.consume(TokenType.IDENTIFIER, "Se esperaba nombre de parámetro").value)
        
        while self.match_token(TokenType.DELIMITER, ","):
            # Verificar que no haya coma extra antes del cierre
            if self.check_token(TokenType.DELIMITER, ")"):
                raise self.error(self.previous(), "Coma extra antes del cierre de paréntesis")
            
            parametros.append(
                self.consume(TokenType.IDENTIFIER, "Se esperaba nombre de parámetro después de ','").value
            )
        
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
        expr = self.expresion()
        return ExpressionStmt(expr)

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
        PRIMARIO → NUMERO | STRING | "True" | "False" | "None" | "(" EXPRESIÓN ")" | IDENTIFICADOR
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
            return Identifier(self.previous().value)
        
        raise self.error(self.peek(), "Se esperaba una expresión")

    def bloque(self):
        """
        BLOQUE → DECLARACIÓN*
        """
        declaraciones = []
        self.indent_level += 1  # Aumentar nivel de indentación esperado
        
        while not self.is_at_end():
            # Verificar indentación
            if not self.check_indentation():
                raise self.error(self.peek(), f"Indentación incorrecta. Se esperaban {self.indent_level * 4} espacios")
            
            try:
                decl = self.declaracion()
                if decl:
                    declaraciones.append(decl)
            except SyntaxError as e:
                self.errors.append(e)
                self.synchronize()
        
        self.indent_level -= 1  # Restaurar nivel de indentación
        return declaraciones
    
    def check_indentation(self) -> bool:
        """Verifica que la indentación sea correcta"""
        if self.peek().position.column != self.indent_level * 4:
            return False
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

    def match_token(self, type: TokenType, value: str) -> bool:
        """Check if current token matches the given type and value"""
        if self.is_at_end():
            return False
        if self.peek().type != type:
            return False
        if self.peek().value != value:
            return False
        self.advance()
        return True

    def match_keyword(self, keyword: str) -> bool:
        """Check if current token is a keyword with the given value"""
        return self.match_token(TokenType.KEYWORD, keyword)

    def check(self, type: TokenType) -> bool:
        """Check if current token is of given type"""
        if self.is_at_end():
            return False
        return self.peek().type == type

    def check_token(self, type: TokenType, value: str) -> bool:
        """Check if current token matches the given type and value"""
        if self.is_at_end():
            return False
        return self.peek().type == type and self.peek().value == value

    def check_keyword(self, keyword: str) -> bool:
        """Check if current token is a keyword with the given value"""
        return self.check_token(TokenType.KEYWORD, keyword)

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
            # Si encontramos un comentario, lo saltamos
            if self.peek().type == TokenType.COMMENT:
                self.advance()
                continue
            
            if self.previous().type == TokenType.DELIMITER and self.previous().value == ";":
                return

            if self.peek().type == TokenType.KEYWORD and self.peek().value in ["def", "class", "if", "while", "return"]:
                return

            self.advance() 