#!/usr/bin/env python3
"""
Script para probar la detección de 'return' fuera de funciones
"""

from ply_lexer import PLYLexer
from ply_parser import PLYParser

# Caso de prueba con un return fuera de función
test_error = '''# Return fuera de función
x = 5
return x  # Esto debería dar error
'''

# Caso de prueba con un return dentro de una función (válido)
test_valid = '''# Return dentro de función (válido)
def suma(a: int, b: int) -> int:
    return a + b

resultado = suma(5, 2)
print(resultado)
'''

def test_return_context():
    print("=== Prueba 1: Return fuera de función (inválido) ===")
    print("Código a analizar:")
    print("-" * 40)
    print(test_error)
    print("-" * 40)
    
    # Crear un lexer y parser
    lexer = PLYLexer(test_error)
    parser = PLYParser(test_error)
    
    # Asegurarse de que el parser reconozca que no estamos en una función
    parser.indent_level = 0
    
    # Intentar parsear el código
    ast = parser.parse(test_error, lexer)
    
    # Verificar si se detectaron errores
    print(f"AST generado: {ast is not None}")
    print("Errores detectados:")
    for error in parser.errors:
        print(f"  - {error}")
    
    if not any("return" in error and "función" in error for error in parser.errors):
        print("❌ No se detectó el error de 'return' fuera de función.")
    else:
        print("✅ Se detectó correctamente el error de 'return' fuera de función.")
    
    print("\n=== Prueba 2: Return dentro de función (válido) ===")
    print("Código a analizar:")
    print("-" * 40)
    print(test_valid)
    print("-" * 40)
    
    # Crear un lexer y parser para el caso válido
    lexer_valid = PLYLexer(test_valid)
    parser_valid = PLYParser(test_valid)
    
    # Asegurarse de que el parser reconozca que estamos en una función
    parser_valid.indent_level = 4
    
    # Intentar parsear el código
    ast_valid = parser_valid.parse(test_valid, lexer_valid)
    
    # Verificar si se detectaron errores
    print(f"AST generado: {ast_valid is not None}")
    print("Errores detectados:")
    for error in parser_valid.errors:
        print(f"  - {error}")
    
    if parser_valid.errors:
        print("❌ Se detectaron errores en código válido con 'return' dentro de función.")
    else:
        print("✅ No se detectaron errores en código válido con 'return' dentro de función.")

if __name__ == "__main__":
    test_return_context() 