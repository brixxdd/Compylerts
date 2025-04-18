import sys
from ply_lexer import PLYLexer
from ply_parser import PLYParser
from typescript_generator import TypeScriptGenerator
from colorama import init, Fore, Style

# Inicializar colorama para salida con color
init()

def compile_to_typescript(source_code: str) -> tuple[str | None, list[str]]:
    """Compila código Python a TypeScript"""
    # Análisis léxico y sintáctico
    lexer = PLYLexer(source_code)
    parser = PLYParser()
    ast = parser.parse(source_code)
    
    if parser.errors or parser.semantic_errors:
        return None, parser.errors + parser.semantic_errors
    
    # Generación de código TypeScript
    generator = TypeScriptGenerator()
    typescript_code = generator.generate(ast)
    
    return typescript_code, []

def main():
    print("=== Compilador Python a TypeScript ===")
    print("Ingresa tu código Python (presiona Ctrl+D en Linux/Mac o Ctrl+Z en Windows para finalizar):")
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
        # Compilar el código a TypeScript
        typescript_code, errors = compile_to_typescript(source_code)
        
        if errors:
            print("\n❌ Errores encontrados:")
            for error in errors:
                if "Error semántico" in error:
                    print(f"{Fore.YELLOW}{error}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}{error}{Style.RESET_ALL}")
        else:
            print("\n✅ Compilación exitosa")
            print("\nCódigo TypeScript generado:")
            print("-" * 40)
            print(typescript_code)
            
    except Exception as e:
        print(f"\n❌ Error inesperado: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()