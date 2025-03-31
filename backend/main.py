import sys
from ply_lexer import PLYLexer
from ply_parser import PLYParser
from colorama import init, Fore, Style

# Inicializar colorama para salida con color
init()

def main():
    print("=== Análisis Léxico y Sintáctico con PLY ===")
    print("Ingresa tu código (presiona Ctrl+D en Linux/Mac o Ctrl+Z en Windows para finalizar):")
    print("-" * 80)
    
    # Leer código fuente
    source_code = ""
    try:
        while True:
            line = input()
            source_code += line + "\n"
    except EOFError:
        pass
    
    # Si no hay código, usar un ejemplo
    if not source_code.strip():
        source_code = """
def suma(a: int, b: int) -> int:
    return a + b

resultado = suma(5, 3)
print(f"La suma es: {resultado}")
"""
        print("Usando código de ejemplo:")
        print(source_code)
    
    # Crear instancia del lexer y parser
    lexer = PLYLexer(source_code)
    parser = PLYParser()
    
    # Realizar análisis
    parser.parse(source_code)
    
    # Obtener errores léxicos
    lexical_errors = lexer.errors
    
    # Mostrar resultados
    if lexical_errors:
        print(f"\n{Fore.RED}❌ Errores Léxicos:{Style.RESET_ALL}")
        for error in lexical_errors:
            print(f"  • {error}")
    else:
        print(f"\n{Fore.GREEN}✅ No se encontraron errores léxicos{Style.RESET_ALL}")
    
    # Filtrar y mostrar errores sintácticos (excluyendo los léxicos)
    syntax_errors = [error for error in parser.errors if "Posible error tipográfico" not in error]
    if syntax_errors:
        print(f"\n{Fore.RED}❌ Errores Sintácticos:{Style.RESET_ALL}")
        for error in syntax_errors:
            print(f"{error}")
            print()  # Línea en blanco para separar errores
    else:
        print(f"\n{Fore.GREEN}✅ Análisis sintáctico completado sin errores{Style.RESET_ALL}")
    
    print("\n¡Análisis completado!")

if __name__ == "__main__":
    main()