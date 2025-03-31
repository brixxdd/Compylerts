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
    
    # Crear instancia del lexer y parser
    lexer = PLYLexer(source_code)
    parser = PLYParser()
    
    # Realizar el análisis léxico
    print("\nTokens encontrados:")
    print("-" * 40)
    tokens_found = []
    while True:
        tok = lexer.token()
        if not tok:
            break
        tokens_found.append(f"{tok.type}: {tok.value}")
    
    # Mostrar tokens encontrados
    for token in tokens_found:
        print(token)
    
    # Verificar errores léxicos
    if lexer.errors:
        print("\n❌ Errores léxicos:")
        for error in lexer.errors:
            print(f"{Fore.RED}{error}{Style.RESET_ALL}")
        return
    
    # Realizar análisis sintáctico
    result = parser.parse(source_code)
    
    # Mostrar errores léxicos primero si existen
    if lexer.errors:
        print("\n❌ Errores léxicos:")
        for error in lexer.errors:
            print(f"{Fore.RED}{error}{Style.RESET_ALL}")
        return
    
    # Mostrar errores sintácticos si existen
    if parser.errors:
        print("\n❌ Errores sintácticos:")
        for error in parser.errors:
            print(f"{Fore.RED}{error}{Style.RESET_ALL}")
        return
    
    print("\n✅ No se encontraron errores léxicos")
    print("✅ Análisis sintáctico completado sin errores")
    
    print("\n¡Análisis completado!")

if __name__ == "__main__":
    main()