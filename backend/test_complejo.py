# Test con varias estructuras de control
numeros = [1, 2, 3, 4, 5]
total = 0

# Bucle for
for numero in numeros:
    # Condicional if-else
    if numero % 2 == 0:
        print("Número par:", numero)
    else:
        print("Número impar:", numero)
    total = total + numero

# Bucle while
contador = 0
while contador < len(numeros):
    valor = numeros[contador]
    print("Posición", contador, "valor:", valor)
    contador = contador + 1

print("Total final:", total) 