from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Set
import re

class ErrorType(Enum):
    """Tipos de errores que puede detectar el compilador"""
    LEXICAL = "LEXICAL"
    SYNTACTIC = "SYNTACTIC"
    SEMANTIC = "SEMANTIC"
    TYPE = "TYPE"  # Nuevo tipo de error

@dataclass
class CompilerError:
    """Clase para representar errores del compilador"""
    
    def __init__(self, type: ErrorType, line: int, message: str, code_line: str = "", column: int = 0, suggestion: str = ""):
        """
        Inicializa un error del compilador
        
        Args:
            type: Tipo de error (léxico, sintáctico, semántico)
            line: Número de línea donde ocurrió el error
            message: Descripción del error
            code_line: Línea de código donde ocurrió el error
            column: Columna donde ocurrió el error
            suggestion: Sugerencia para corregir el error
        """
        self.type = type
        self.line = line
        self.message = message
        self.code_line = code_line
        self.column = column
        self.suggestion = suggestion
    
    def __eq__(self, other):
        if not isinstance(other, CompilerError):
            return False
        return (self.type == other.type and
                self.line == other.line and
                self.message == other.message and
                self.column == other.column)
    
    def __hash__(self):
        return hash((self.type, self.line, self.message, self.column))

class ErrorHandler:
    """Manejador de errores del compilador"""
    
    def __init__(self):
        """Inicializa el manejador de errores"""
        self.errors: List[CompilerError] = []
        self.function_advice_added = False
        
    def add_error(self, error: CompilerError):
        """
        Añade un error a la lista de errores
        
        Args:
            error: Error a añadir
        """
        # Verificar si el error ya existe
        if error not in self.errors:
            self.errors.append(error)
    
    def has_errors(self) -> bool:
        """
        Verifica si hay errores
        
        Returns:
            True si hay errores, False en caso contrario
        """
        return len(self.errors) > 0
    
    def get_errors_by_type(self, error_type: ErrorType) -> List[CompilerError]:
        """
        Obtiene los errores de un tipo específico
        
        Args:
            error_type: Tipo de error a filtrar
            
        Returns:
            Lista de errores del tipo especificado
        """
        return [error for error in self.errors if error.type == error_type]
    
    def clear_errors(self):
        """Limpia la lista de errores"""
        self.errors = []
        self.function_advice_added = False
    
    def remove_function_errors(self, defined_functions: Set[str]):
        """
        Elimina errores relacionados con funciones que en realidad están definidas
        
        Args:
            defined_functions: Conjunto de nombres de funciones definidas
        """
        to_remove = []
        for i, error in enumerate(self.errors):
            if (error.type == ErrorType.SEMANTIC and 
                "Función '" in error.message and 
                "' no está definida" in error.message):
                
                # Extraer el nombre de la función
                func_name = error.message.split("'")[1]
                if func_name in defined_functions:
                    to_remove.append(i)
        
        # Eliminar los errores de atrás hacia adelante para no afectar los índices
        for i in sorted(to_remove, reverse=True):
            self.errors.pop(i)
    
    def check_type_compatibility(self, left_type: str, right_type: str, operation: str, line: int, code_line: str, column: int):
        """
        Verifica si dos tipos son compatibles para una operación
        
        Args:
            left_type: Tipo del operando izquierdo
            right_type: Tipo del operando derecho
            operation: Operación que se está realizando
            line: Número de línea donde ocurre la operación
            code_line: Línea de código donde ocurre la operación
            column: Columna donde ocurre la operación
        
        Returns:
            True si los tipos son compatibles, False en caso contrario
        """
        # Para la operación de suma
        if operation == '+':
            # Verificar tipos incompatibles para suma
            incompatible_types = {
                ('int', 'str'): "No se puede sumar un entero con un string",
                ('str', 'int'): "No se puede sumar un string con un entero",
                ('bool', 'str'): "No se puede sumar un booleano con un string",
                ('str', 'bool'): "No se puede sumar un string con un booleano",
            }
            
            key = (left_type, right_type)
            if key in incompatible_types:
                self.add_error(CompilerError(
                    type=ErrorType.TYPE,
                    line=line,
                    message=f"Error de tipo: {incompatible_types[key]}",
                    code_line=code_line,
                    column=column,
                    suggestion=f"Convierte los tipos manualmente antes de operarlos: str({left_type})" if left_type != 'str' else f"Convierte los tipos manualmente antes de operarlos: str({right_type})"
                ))
                return False
        
        # Para la operación de resta, multiplicación y división
        elif operation in ['-', '*', '/']:
            # Verificar incompatibilidades para otras operaciones aritméticas
            if left_type == 'str' or right_type == 'str':
                operation_names = {'-': 'restar', '*': 'multiplicar', '/': 'dividir'}
                self.add_error(CompilerError(
                    type=ErrorType.TYPE,
                    line=line,
                    message=f"Error de tipo: No se puede {operation_names[operation]} un string",
                    code_line=code_line,
                    column=column,
                    suggestion=f"Las operaciones aritméticas '{operation}' no se pueden realizar con strings"
                ))
                return False
        
        return True
    
    def format_errors(self) -> str:
        """
        Formatea los errores para mostrarlos al usuario
        
        Returns:
            Errores formateados como string
        """
        if not self.errors:
            return "No se encontraron errores."
        
        # Ordenar errores por tipo y línea
        self.errors.sort(key=lambda e: (e.type.value, e.line))
        
        # Agrupar por tipo
        error_by_type = {}
        for error in self.errors:
            if error.type not in error_by_type:
                error_by_type[error.type] = []
            error_by_type[error.type].append(error)
        
        result = "\n❌ Errores encontrados:\n"
        
        for error_type, errors in error_by_type.items():
            result += f"\n{error_type.value}:\n"
            for error in errors:
                # Añadir información de línea y mensaje
                result += f"  Línea {error.line}: {error.message}\n"
                
                # Añadir la línea de código si está disponible
                if error.code_line:
                    result += f"  En el código:\n      {error.code_line}\n"
                    
                    # Añadir marcador que apunte al error
                    if error.column >= 0:
                        result += f"      {' ' * error.column}^ Aquí\n"
                
                # Añadir sugerencia si está disponible
                if error.suggestion:
                    result += f"  Sugerencia: {error.suggestion}\n"
        
        # Agregar consejos para errores comunes (solo una vez)
        if any(e.type == ErrorType.SEMANTIC and "función" in e.message.lower() for e in self.errors):
            result += "\nConsejo: Asegúrate de que todas las funciones que usas estén definidas antes de llamarlas."
            self.function_advice_added = True
        
        return result

# Crear una instancia global del manejador de errores
error_handler = ErrorHandler() 