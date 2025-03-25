from lexer import LexicalAnalyzer
from parser import Parser
import json

def node_to_dict(obj):
    """Convert AST nodes to dictionaries for JSON serialization"""
    if hasattr(obj, "__dict__"):
        result = {}
        for key, value in obj.__dict__.items():
            if key.startswith("_"):
                continue
            result[key] = node_to_dict(value)
        return result
    elif isinstance(obj, list):
        return [node_to_dict(item) for item in obj]
    else:
        return obj

def main():
    analyzer = LexicalAnalyzer()
    
    print("Bienvenido al compilador")
    print("Ingresa tu código (presiona Ctrl+D o Ctrl+Z para finalizar):")
    
    try:
        # Leer múltiples líneas hasta EOF
        lines = []
        while True:
            try:
                line = input()
                lines.append(line)
            except EOFError:
                break
        
        source_code = '\n'.join(lines)
        
        # Análisis léxico
        print("\n=== Análisis Léxico ===")
        tokens = analyzer.tokenize(source_code)
        analyzer.print_tokens()
        analyzer.print_errors()
        
        if not analyzer.errors:
            # Análisis sintáctico
            print("\n=== Análisis Sintáctico ===")
            parser = Parser(tokens)
            ast = parser.parse()
            
            if parser.errors:
                print("\nErrores sintácticos encontrados:")
                for error in parser.errors:
                    print(f"  {error}")
            else:
                print("\nAnálisis sintáctico completado con éxito!")
                print("\nÁrbol de Sintaxis Abstracta (AST):")
                ast_dict = node_to_dict(ast)
                print(json.dumps(ast_dict, indent=2, ensure_ascii=False))
    
    except Exception as e:
        print(f"\nError inesperado: {e}")

if __name__ == "__main__":
    main() 