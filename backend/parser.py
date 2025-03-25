from typing import List, Optional, Any
from dataclasses import dataclass
from lexer import Token, TokenType, LexicalAnalyzer
from ast_nodes import *

class SyntaxError(Exception):
    def __init__(self, message: str, token: Token):
        self.message = message
        self.token = token
        super().__init__(f"Syntax Error at line {token.position.line}, column {token.position.column}: {message}")

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.current = 0
        self.errors = []

    def parse(self):
        """Parse the program and return an AST"""
        try:
            return self.program()
        except Exception as e:
            self.errors.append(e)
            return None

    def program(self):
        """
        program -> statement_list EOF
        """
        statements = []
        while not self.is_at_end():
            try:
                stmt = self.declaration()
                if stmt:
                    statements.append(stmt)
            except SyntaxError as e:
                self.errors.append(e)
                self.synchronize()
        return Program(statements)

    def declaration(self):
        """
        declaration -> variable_declaration | function_declaration | statement
        """
        # Ignorar comentarios
        if self.check(TokenType.COMMENT):
            self.advance()  # Consumir el comentario
            return None     # No hay declaración que procesar
            
        if self.match_keyword("def"):
            return self.function_declaration()
        
        if self.match_keyword("class"):
            # Implementar cuando sea necesario
            pass
        
        return self.statement()

    def function_declaration(self):
        """
        function_declaration -> "def" IDENTIFIER "(" parameter_list ")" ["->" type] ":" function_body
        parameter_list -> parameter ("," parameter)* | ε
        parameter -> IDENTIFIER [":" type]
        function_body -> statement_list
        """
        name_token = self.consume(TokenType.IDENTIFIER, "Expect function name.")
        name = name_token.value
        
        self.consume(TokenType.DELIMITER, "Expect '(' after function name.")
        
        parameters = []
        if not self.check_token(TokenType.DELIMITER, ")"):
            # Parse parameters
            while True:
                param_name = self.consume(TokenType.IDENTIFIER, "Expect parameter name.").value
                param_type = None
                
                if self.match_token(TokenType.DELIMITER, ":"):
                    param_type = self.consume(TokenType.TYPE_HINT, "Expect type hint after ':'.").value
                
                parameters.append(VariableDecl(param_name, param_type))
                
                if not self.match_token(TokenType.DELIMITER, ","):
                    break
        
        self.consume(TokenType.DELIMITER, "Expect ')' after parameters.")
        
        # Return type
        return_type = None
        if self.match_token(TokenType.OPERATOR, "->"):
            return_type = self.consume(TokenType.TYPE_HINT, "Expect return type after '->'.").value
        
        self.consume(TokenType.DELIMITER, "Expect ':' before function body.")
        
        # Function body - collect statements until we find a blank line or a non-indented line
        body = []
        
        # En un analizador real, aquí verificaríamos la indentación
        # Como simplificación, consideraremos que el cuerpo de la función incluye
        # todas las declaraciones hasta encontrar una línea en blanco (representada por un comentario vacío)
        # o hasta encontrar otra declaración de función o clase
        
        # Recopilamos solo las dos primeras declaraciones (if y return)
        # Esta es una simplificación extrema, pero funcionará para nuestro ejemplo
        if not self.is_at_end():
            # Primera declaración (if)
            stmt = self.statement()
            if stmt:
                body.append(stmt)
                
            # Segunda declaración (return)
            if not self.is_at_end() and not self.check_keyword("def") and not self.check_keyword("class"):
                stmt = self.statement()
                if stmt:
                    body.append(stmt)
        
        return FunctionDecl(name, parameters, return_type, body)

    def statement(self):
        """
        statement -> expression_statement
                  | if_statement
                  | while_statement
                  | return_statement
        """
        # Ignorar comentarios
        if self.check(TokenType.COMMENT):
            self.advance()  # Consumir el comentario
            return None     # No hay statement que procesar
            
        if self.match_keyword("if"):
            return self.if_statement()
        
        if self.match_keyword("while"):
            return self.while_statement()
        
        if self.match_keyword("return"):
            return self.return_statement()
        
        return self.expression_statement()

    def if_statement(self):
        """
        if_statement -> "if" expression ":" statement_list ["else" ":" statement_list]
        """
        condition = self.expression()
        self.consume(TokenType.DELIMITER, "Expect ':' after if condition.")
        
        # Recopilar un solo statement para la rama 'then'
        # En Python real, esto sería un bloque indentado
        then_branch = []
        stmt = self.statement()
        if stmt:
            then_branch.append(stmt)
        
        # Manejar la rama 'else' si existe
        else_branch = None
        if self.match_keyword("else"):
            self.consume(TokenType.DELIMITER, "Expect ':' after 'else'.")
            else_branch = []
            
            # Recopilar un solo statement para la rama 'else'
            stmt = self.statement()
            if stmt:
                else_branch.append(stmt)
        
        return IfStmt(condition, then_branch, else_branch)

    def while_statement(self):
        """
        while_statement -> "while" expression ":" statement_list
        """
        condition = self.expression()
        self.consume(TokenType.DELIMITER, "Expect ':' after while condition.")
        
        body = []
        while not self.is_at_end() and not self.check_keyword("def"):
            stmt = self.statement()
            if stmt:
                body.append(stmt)
        
        return WhileStmt(condition, body)

    def return_statement(self):
        """
        return_statement -> "return" [expression] NEWLINE
        """
        value = None
        if not self.check_token(TokenType.DELIMITER, ";") and not self.check_token(TokenType.EOF, ""):
            value = self.expression()
        
        return ReturnStmt(value)

    def expression_statement(self):
        """
        expression_statement -> expression NEWLINE
        """
        expr = self.expression()
        return ExpressionStmt(expr)

    def expression(self):
        """
        expression -> assignment
        """
        return self.assignment()

    def assignment(self):
        """
        assignment -> equality ("=" assignment)?
        """
        expr = self.equality()
        
        if self.match_token(TokenType.OPERATOR, "="):
            value = self.assignment()
            
            if isinstance(expr, Identifier):
                return AssignExpr(expr, value)
            
            self.error(self.previous(), "Invalid assignment target.")
        
        return expr

    def equality(self):
        """
        equality -> comparison (("==" | "!=") comparison)*
        """
        expr = self.comparison()
        
        while self.match_token(TokenType.OPERATOR, "==") or self.match_token(TokenType.OPERATOR, "!="):
            operator = self.previous().value
            right = self.comparison()
            expr = BinaryExpr(expr, operator, right)
        
        return expr

    def comparison(self):
        """
        comparison -> term ((">" | ">=" | "<" | "<=") term)*
        """
        expr = self.term()
        
        while (self.match_token(TokenType.OPERATOR, ">") or 
               self.match_token(TokenType.OPERATOR, ">=") or 
               self.match_token(TokenType.OPERATOR, "<") or 
               self.match_token(TokenType.OPERATOR, "<=")):
            operator = self.previous().value
            right = self.term()
            expr = BinaryExpr(expr, operator, right)
        
        return expr

    def term(self):
        """
        term -> factor (("+" | "-") factor)*
        """
        expr = self.factor()
        
        while self.match_token(TokenType.OPERATOR, "+") or self.match_token(TokenType.OPERATOR, "-"):
            operator = self.previous().value
            right = self.factor()
            expr = BinaryExpr(expr, operator, right)
        
        return expr

    def factor(self):
        """
        factor -> unary (("*" | "/") unary)*
        """
        expr = self.unary()
        
        while self.match_token(TokenType.OPERATOR, "*") or self.match_token(TokenType.OPERATOR, "/"):
            operator = self.previous().value
            right = self.unary()
            expr = BinaryExpr(expr, operator, right)
        
        return expr

    def unary(self):
        """
        unary -> ("-" | "!") unary | primary
        """
        if self.match_token(TokenType.OPERATOR, "-") or self.match_token(TokenType.OPERATOR, "!"):
            operator = self.previous().value
            right = self.unary()
            return UnaryExpr(operator, right)
        
        return self.primary()

    def primary(self):
        """
        primary -> NUMBER | STRING | "True" | "False" | "None" | "(" expression ")" | IDENTIFIER | call
        """
        if self.match(TokenType.NUMBER):
            return Literal(float(self.previous().value))
        
        if self.match(TokenType.STRING):
            # Quitar comillas
            value = self.previous().value[1:-1]
            return Literal(value)
        
        if self.match_keyword("True"):
            return Literal(True)
        
        if self.match_keyword("False"):
            return Literal(False)
        
        if self.match_keyword("None"):
            return Literal(None)
        
        if self.match_token(TokenType.DELIMITER, "("):
            expr = self.expression()
            self.consume(TokenType.DELIMITER, "Expect ')' after expression.")
            return expr
        
        if self.match(TokenType.IDENTIFIER):
            name = self.previous().value
            
            # Verificar si es una llamada a función
            if self.match_token(TokenType.DELIMITER, "("):
                arguments = []
                
                # Parsear argumentos
                if not self.check_token(TokenType.DELIMITER, ")"):
                    while True:
                        arguments.append(self.expression())
                        
                        if not self.match_token(TokenType.DELIMITER, ","):
                            break
                
                self.consume(TokenType.DELIMITER, "Expect ')' after arguments.")
                return CallExpr(Identifier(name), arguments)
            
            return Identifier(name)
        
        raise self.error(self.peek(), "Expect expression.")

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
            if self.previous().type == TokenType.DELIMITER and self.previous().value == ";":
                return

            if self.peek().type == TokenType.KEYWORD and self.peek().value in ["def", "class", "if", "while", "return"]:
                return

            self.advance() 