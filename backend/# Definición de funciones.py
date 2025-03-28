# Definición de funciones
def calcular_area(radio):
    return 3.14 * radio * radio

def suma(a, b):
    resultado = a + b
    return resultado

def factorial(n):
    if n <= 1:
        return 1
    else:
        return n * factorial(n - 1)

# Variables y expresiones
x = 10
y = 20
z = suma(x, y)

# Estructuras de control
if z > 25:
    print("La suma es mayor que 25")
    area = calcular_area(z / 10)
    print("El área del círculo es:", area)
else:
    print("La suma es menor o igual a 25")
    fact = factorial(5)
    print("El factorial de 5 es:", fact)

# Bucles
for i in range(1, 6):
    print("Iteración:", i)
    if i % 2 == 0:
        print("Número par")
    else:
        print("Número impar")

# Clases
class Persona:
    def __init__(self, nombre, edad):
        self.nombre = nombre
        self.edad = edad
    
    def saludar(self):
        return "Hola, mi nombre es " + self.nombre

# Crear instancias
persona1 = Persona("Juan", 30)
mensaje = persona1.saludar()
print(mensaje)