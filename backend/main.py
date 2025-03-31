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
    
    try:
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
        
        # Realizar análisis sintáctico y semántico
        result = parser.parse(source_code)
        
        # Mostrar errores sintácticos y semánticos
        if parser.errors:
            print("\n❌ Errores encontrados:")
            for error in parser.errors:
                print(f"{Fore.RED}{error}{Style.RESET_ALL}")
        elif parser.semantic_errors:
            print("\n❌ Errores semánticos:")
            for error in parser.semantic_errors:
                print(f"{Fore.YELLOW}{error}{Style.RESET_ALL}")
        else:
            print("\n✅ No se encontraron errores")
            print("✅ Análisis completado sin errores")
            
    except Exception as e:
        print(f"\n❌ Error inesperado: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()