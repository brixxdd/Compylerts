# Prueba de errores semánticos

# 1. Variables no definidas
def prueba_variables_no_definidas():
    x = y + 10  # Error: 'y' no está definida

# 2. Tipos incompatibles
def prueba_tipos_incompatibles():
    nombre = "Juan"
    edad = 25
    resultado = nombre + edad  # Error: no se puede concatenar str con int

# 3. Función no definida
def prueba_funcion_no_definida():
    calcular_total()  # Error: función no definida

# 4. Tipo de retorno incorrecto
def prueba_tipo_retorno_incorrecto() -> str:
    return 42  # Error: retorna int cuando debería retornar str

# 5. Variable usada antes de asignación
def prueba_variable_antes_asignacion():
    total = precio * cantidad  # Error: 'precio' y 'cantidad' no están definidas

# 6. Llamada a función con tipos incorrectos
def prueba_tipos_argumentos_incorrectos():
    def sumar(a: int, b: int) -> int:
        return a + b

    resultado = sumar("5", 10)  # Error: tipo incorrecto en argumento

# 7. Variable indefinida en print
def prueba_variable_indefinida():
    print(contador)  # Error: 'contador' no está definida

# 8. Uso de función antes de definirla
def prueba_funcion_antes_definicion():
    multiplicar(5, 3)  # Error: función usada antes de definirla

    def multiplicar(x: int, y: int) -> int:
        return x * y

# 9. Asignación a tipo incorrecto
def prueba_asignacion_tipo_incorrecto():
    numero: int = "123"  # Error: asignando str a variable tipo int

# 10. Uso de operador con tipos incompatibles
def prueba_operador_tipos_incompatibles():
    lista = [1, 2, 3]
    resultado = lista + 5  # Error: no se puede sumar lista con número

# Función principal para ejecutar las pruebas
def main():
    print("Iniciando pruebas semánticas...")
    # Las funciones no se ejecutan realmente, solo se compilan
    print("Pruebas completadas.")

if __name__ == "__main__":
    main() 