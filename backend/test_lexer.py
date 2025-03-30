import unittest
from lexer import LexicalAnalyzer, TokenType

class TestLexicalAnalyzer(unittest.TestCase):
    def setUp(self):
        self.lexer = LexicalAnalyzer("test_file.py")

    def test_basic_python(self):
        source = """
def suma(a: int, b: int) -> int:
    # Suma dos números
    return a + b  # retorna la suma
"""
        tokens = self.lexer.tokenize(source)
        self.assertTrue(any(t.type == TokenType.KEYWORD and t.value == 'def' for t in tokens))
        self.assertTrue(any(t.type == TokenType.TYPE_HINT and t.value == 'int' for t in tokens))
        self.assertTrue(any(t.type == TokenType.ARROW for t in tokens))

    def test_typescript_features(self):
        source = """
interface Usuario {
    nombre: string;
    edad?: number;
    readonly id: string;
}

async def get_user() -> Usuario:
    await db.fetch()
    return user
"""
        tokens = self.lexer.tokenize(source)
        self.assertTrue(any(t.type == TokenType.KEYWORD and t.value == 'interface' for t in tokens))
        self.assertTrue(any(t.type == TokenType.TYPE_HINT and t.value == 'string' for t in tokens))
        self.assertTrue(any(t.type == TokenType.ASYNC for t in tokens))

    def test_template_strings(self):
        source = '''
mensaje = f"Hola {nombre}!"
template = `Hello ${name}!`
'''
        tokens = self.lexer.tokenize(source)
        self.assertTrue(any(t.type == TokenType.TEMPLATE_STRING for t in tokens))

    def test_operators(self):
        source = """
x = a ?? b
y = obj?.prop
z = value!.method()
"""
        tokens = self.lexer.tokenize(source)
        self.assertTrue(any(t.value == '??' for t in tokens))
        self.assertTrue(any(t.value == '?.' for t in tokens))
        self.assertTrue(any(t.value == '!.' for t in tokens))

    def test_error_handling(self):
        source = "let x = $123"  # $ es un caracter ilegal
        tokens = self.lexer.tokenize(source)
        self.assertTrue(len(self.lexer.errors) > 0)
        self.assertTrue(any(t.type == TokenType.ERROR for t in tokens))

# Código de ejemplo
if __name__ == "__main__":
    # Ejemplo 1: Código Python básico
    print("\n=== Ejemplo 1: Código Python básico ===")
    source_code = """
def suma(a: int, b: int) -> int:
    # Suma dos números
    return a + b  # retorna la suma
"""
    analyzer = LexicalAnalyzer("ejemplo1.py")
    tokens = analyzer.tokenize(source_code)
    analyzer.print_tokens()
    analyzer.print_errors()

    # Ejemplo 2: Características de TypeScript
    print("\n=== Ejemplo 2: Características de TypeScript ===")
    source_code = """
interface Usuario {
    nombre: string;
    edad?: number;
    readonly id: string;
}

async def get_user() -> Usuario:
    await db.fetch()
    return user
"""
    analyzer = LexicalAnalyzer("ejemplo2.py")
    tokens = analyzer.tokenize(source_code)
    analyzer.print_tokens()
    analyzer.print_errors()

    # Ejecutar pruebas unitarias
    unittest.main(argv=[''], exit=False)
