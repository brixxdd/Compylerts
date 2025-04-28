#!/usr/bin/env python3
"""
Script para probar la detección de strings sin cerrar
"""

from ply_lexer import PLYLexer
from ply_parser import PLYParser

# Caso de prueba con un string sin cerrar
test_code = '''# Algunas variables y operaciones básicas
nombre = "Python
edad = 30
precio = 19.99
'''

def test_unclosed_string():
    print("=== Prueba de detección de strings sin cerrar ===")
    print("Código a analizar:")
    print("-" * 40)
    print(test_code)
    print("-" * 40)
    
    # Crear un lexer
    lexer = PLYLexer(test_code)
    
    # Consumir todos los tokens para asegurar que se detecten errores
    tokens = []
    while True:
        token = lexer.token()
        if not token:
            break
        tokens.append(token)
    
    # Verificar si se detectaron errores
    print(f"Código válido: {lexer.valid_code}")
    print("Errores detectados:")
    for error in lexer.errors:
        print(f"  - {error}")
    
    if not lexer.errors:
        print("¡ERROR! No se detectaron errores en el código con string sin cerrar.")
    else:
        print("✅ Se detectaron correctamente los errores en el código.")

if __name__ == "__main__":
    test_unclosed_string() 