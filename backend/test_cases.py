# Casos de prueba para el compilador Python a TypeScript

# 1. Función simple con return
TEST_FUNCTION_SIMPLE = """
def suma(a: int, b: int) -> int:
    return a + b

resultado = suma(5, 3)
print(resultado)
"""

# 2. Error: return fuera de función
TEST_RETURN_ERROR = """
x = 5
return x  # Error: return fuera de función
"""

# 3. Error: string sin cerrar
TEST_UNCLOSED_STRING = """
nombre = "Juan
apellido = "Pérez"
"""

# 4. Error: falta de coma entre elementos
TEST_MISSING_COMMA = """
frutas = ["manzana" "naranja" "banana"]
"""

# 5. Error: combinación de varios errores
TEST_MULTIPLE_ERRORS = """
def calcular(x):
    return x * 2

valores = [1, 2, 3
return "Resultado: " + str(calcular(5))  # Error: return fuera de función y string sin cerrar
"""

# 6. Caso válido: estructuras de control anidadas
TEST_NESTED_STRUCTURES = """
def procesar_lista(items: list) -> list:
    resultados = []
    for item in items:
        if item > 0:
            resultados.append(item * 2)
        else:
            resultados.append(0)
    return resultados

numeros = [-2, 0, 3, 5]
resultado = procesar_lista(numeros)
print(resultado)
"""

# 7. Errores de sintaxis específicos
TEST_SYNTAX_ERRORS = """
# Falta el paréntesis de cierre
if (x > 5:
    print("Mayor que 5")

# Falta los dos puntos
for i in range(10)
    print(i)
"""

# Función para ejecutar los casos de prueba
def run_test(test_name, test_code):
    """Ejecuta un caso de prueba y muestra los resultados"""
    from ply_lexer import PLYLexer
    from ply_parser import PLYParser
    
    print(f"\n=== Ejecutando prueba: {test_name} ===")
    print("Código a analizar:")
    print("-" * 40)
    print(test_code)
    print("-" * 40)
    
    # Analizar con el lexer
    lexer = PLYLexer(test_code)
    
    # Verificar errores léxicos
    lexer_errors = []
    while True:
        token = lexer.token()
        if not token:
            break
    
    if lexer.errors:
        print("\nErrores léxicos encontrados:")
        for error in lexer.errors:
            print(f"  - {error}")
    
    # Analizar con el parser
    parser = PLYParser(test_code)
    ast = parser.parse(test_code, PLYLexer(test_code))
    
    if parser.errors:
        print("\nErrores sintácticos encontrados:")
        for error in parser.errors:
            print(f"  - {error}")
    
    if not lexer.errors and not parser.errors:
        print("\n✅ Análisis completado sin errores")
    
    print("\n" + "="*50)
    
if __name__ == "__main__":
    # Ejecutar todos los casos de prueba
    run_test("Función simple con return", TEST_FUNCTION_SIMPLE)
    run_test("Return fuera de función", TEST_RETURN_ERROR)
    run_test("String sin cerrar", TEST_UNCLOSED_STRING)
    run_test("Falta de coma entre elementos", TEST_MISSING_COMMA)
    run_test("Múltiples errores", TEST_MULTIPLE_ERRORS)
    run_test("Estructuras anidadas válidas", TEST_NESTED_STRUCTURES)
    run_test("Errores de sintaxis específicos", TEST_SYNTAX_ERRORS) 