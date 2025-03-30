from lexer import LexicalAnalyzer
import sys

def main():
    analyzer = LexicalAnalyzer("input.py")
    
    print("Bienvenido al Analizador Léxico Python -> TypeScript")
    print("Ingresa tu código (presiona Ctrl+D en Linux/Mac o Ctrl+Z en Windows para finalizar):")
    print("Para probar código con errores, puedes usar caracteres ilegales como $ o números inválidos")
    print("-" * 80)
    
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
        
        # Si no hay código, usar ejemplos
        if not source_code.strip():
            print("\nUsando código de ejemplo...")
            print("\n=== Ejemplo 1: Código Python/TypeScript válido ===")
            source_code = '''
# Definición de una interfaz TypeScript
interface Usuario {
    nombre: string;
    edad?: number;
    readonly id: string;
}

# Función asíncrona con tipos
async def get_user(id: string) -> Usuario:
    # Template string
    query = f"SELECT * FROM users WHERE id = {id}"
    
    # Operadores de TypeScript
    result = await db?.query(query) ?? default_user
    
    if result?.nombre:
        return result
    else:
        raise ValueError("Usuario no encontrado")
'''
            analyzer.tokenize(source_code)
            analyzer.print_tokens()
            analyzer.print_errors()

            print("\n=== Ejemplo 2: Código con errores ===")
            source_code = '''
# Error: caracteres ilegales
let salary = $1000

# Error: número inválido
x = 12.34.56

# Error: template string mal formado
msg = f"Hola {nombre"

# Error: operador inválido
y = a $$$ b
'''
            analyzer.tokenize(source_code)
            analyzer.print_tokens()
            analyzer.print_errors()
        else:
            # Análisis léxico del código ingresado
            print("\n=== Análisis Léxico ===")
            analyzer.tokenize(source_code)
            analyzer.print_tokens()
            analyzer.print_errors()
    
    except KeyboardInterrupt:
        print("\nAnálisis cancelado por el usuario")
    except Exception as e:
        print(f"\nError inesperado: {e}")

if __name__ == "__main__":
    main()