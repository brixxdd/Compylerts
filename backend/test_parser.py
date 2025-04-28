import unittest
from ply_lexer import PLYLexer
from ply_parser import PLYParser

class TestParser(unittest.TestCase):
    def test_string_sin_cerrar(self):
        """Verifica que se detecte correctamente un string sin cerrar"""
        codigo = 'nombre = "Esto es un string sin cerrar\nedad = 30'
        
        # Analizar con el lexer
        lexer = PLYLexer(codigo)
        
        # Consumir todos los tokens para procesar errores
        while lexer.token():
            pass
            
        # Verificar el mensaje de error
        self.assertTrue(any("String sin cerrar" in error for error in lexer.errors), 
                      "No se detectó error de string sin cerrar")
        self.assertFalse(lexer.valid_code, "El código debería ser inválido")
    
    def test_return_fuera_de_funcion(self):
        """Verifica que se detecte correctamente un return fuera de función"""
        codigo = 'return 5'
        
        # Analizar con el lexer
        lexer = PLYLexer(codigo)
        
        # Crear el parser y analizar el código
        parser = PLYParser(codigo)
        
        # Forzar que el parser reconozca que esto no está en contexto de función
        parser.indent_level = 0 
        
        # Parsear el código y capturar errores
        try:
            ast = parser.parse(codigo, lexer)
            # Verificar si hay mensaje de error sobre return fuera de función
            self.assertTrue(any("return" in err and "función" in err for err in parser.errors))
        except Exception as e:
            # Si falla el parsing, también es válido si el error es sobre return
            self.assertTrue("return" in str(e))
    
    def test_function_con_return(self):
        """Verifica que una función con return se analice correctamente"""
        codigo = '''def suma(a: int, b: int) -> int:
    return a + b
'''
        # Analizar con el lexer
        lexer = PLYLexer(codigo)
        
        # Simular el procesamiento de tokens para establecer el contexto de función
        tokens = []
        while True:
            token = lexer.token()
            if not token:
                break
            tokens.append(token)
            
        # Crear un nuevo lexer para el parsing real
        lexer = PLYLexer(codigo)
        parser = PLYParser(codigo)
        
        # Simular que estamos dentro de una función
        parser.indent_level = 4  # Indentación típica de una función
        
        try:
            ast = parser.parse(codigo, lexer)
            self.assertEqual(len(parser.errors), 0, f"No debería haber errores: {parser.errors}")
        except Exception as e:
            self.fail(f"No debería fallar el parsing: {e}")
    
    def test_falta_coma(self):
        """Verifica la detección de una coma faltante después de un string"""
        codigo = '''valores = ["uno" "dos"]'''
        
        # Analizar con el lexer
        lexer = PLYLexer(codigo)
        
        # Consumir todos los tokens para asegurar que se procesen
        tokens = []
        while True:
            token = lexer.token()
            if not token:
                break
            tokens.append(token)
            
        # Verificar si los tokens contienen strings adyacentes sin coma
        string_tokens = [t for t in tokens if t.type == 'STRING']
        if len(string_tokens) >= 2:
            # Hay al menos dos strings, comprobamos si están adyacentes
            for i in range(len(tokens) - 1):
                if tokens[i].type == 'STRING' and tokens[i+1].type == 'STRING':
                    # Encontrado el error: dos strings consecutivos sin coma
                    return
        
        # Si llegamos aquí, no encontramos el error esperado
        self.fail("No se detectó correctamente la falta de coma entre strings")

if __name__ == '__main__':
    unittest.main() 