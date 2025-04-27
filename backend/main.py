import sys
from ply_lexer import PLYLexer
from ply_parser import PLYParser
from typescript_generator import TypeScriptGenerator
from ast_nodes import print_ast
from colorama import init, Fore, Style

# Inicializar colorama para salida con color
init()

def compile_to_typescript(source_code: str) -> tuple[str | None, list[str]]:
    """Compila código Python a TypeScript"""
    try:
        # Crear el lexer y parser
        lexer = PLYLexer(source_code)
        
        # Si hay errores en el lexer o el código no es válido, retornar los errores inmediatamente
        if not lexer.valid_code:
            return None, lexer.errors
        
        parser = PLYParser(source_code)
        
        # Parsear el código
        ast = parser.parser.parse(input=source_code, lexer=lexer.lexer)
        
        # Si hay errores en el parser, retornarlos
        if parser.errors:
            return None, parser.errors
        
        if ast:
            print("\n=== AST Generated ===")
            print_ast(ast)
            print("===================\n")
            
            # Generación de código TypeScript
            generator = TypeScriptGenerator()
            typescript_code = generator.generate(ast)
            return typescript_code, []
        else:
            return None, ["Error: No se pudo generar el AST"]
            
    except Exception as e:
        return None, [f"❌ Error inesperado: {str(e)}"]

def main():
    print("=== Compilador Python a TypeScript ===")
    print("Ingresa tu código Python (presiona Ctrl+D en Linux/Mac o Ctrl+Z en Windows para finalizar):")
    print("-" * 80)
    
    # Leer el código fuente
    try:
        source_code = ""
        while True:
            try:
                line = input()
                source_code += line + "\n"
            except EOFError:
                break
            except KeyboardInterrupt:
                print("\nCompilación cancelada")
                return
    except Exception as e:
        print(f"\n❌ Error al leer el código: {str(e)}")
        return
    
    # Compilar el código
    typescript_code, errors = compile_to_typescript(source_code)
    
    # Mostrar errores si los hay
    if errors:
        print("\n❌ Errores encontrados:")
        for error in errors:
            print(error)
        return
    
    # Mostrar el código TypeScript generado
    print("\n✅ Compilación exitosa\n")
    print("Código TypeScript generado:")
    print("-" * 40)
    print(typescript_code)

if __name__ == "__main__":
    main()