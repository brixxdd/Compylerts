from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional
import re

class ErrorType(Enum):
    LEXICAL = auto()
    SYNTACTIC = auto()
    SEMANTIC = auto()

@dataclass
class CompilerError:
    type: ErrorType
    line: int
    message: str
    code_line: str
    column: int
    suggestion: Optional[str] = None
    
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
    def __init__(self):
        self.errors: List[CompilerError] = []
        self.function_advice_added = False
        
    def add_error(self, error: CompilerError):
        # Evitar agregar errores duplicados
        if error in self.errors:
            return
        self.errors.append(error)
    
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    def get_errors_by_type(self, error_type: ErrorType) -> List[CompilerError]:
        return [e for e in self.errors if e.type == error_type]
    
    def clear_errors(self):
        """Limpia todos los errores acumulados"""
        self.errors = []
        self.function_advice_added = False
    
    def remove_function_errors(self, defined_functions):
        """Elimina errores de 'función no definida' para funciones que están definidas"""
        if not defined_functions:
            return
            
        filtered_errors = []
        for error in self.errors:
            # Si es un error de función no definida, verificar si realmente está definida
            if (error.type == ErrorType.SEMANTIC and 
                "función" in error.message.lower() and 
                "no está definida" in error.message.lower()):
                # Extraer el nombre de la función del mensaje de error
                func_match = re.search(r"'([^']+)'", error.message)
                if func_match:
                    func_name = func_match.group(1)
                    # Si la función está definida, no incluir el error
                    if func_name in defined_functions:
                        continue
            filtered_errors.append(error)
        
        # Actualizar la lista de errores
        self.errors = filtered_errors
    
    def format_errors(self) -> str:
        if not self.errors:
            return ""
        
        # Asegurarnos de que no hay duplicados
        unique_errors = set()
        for error in self.errors:
            unique_errors.add(error)
        
        # Convertir a lista y ordenar
        unique_errors_list = list(unique_errors)
        unique_errors_list.sort(key=lambda x: (x.type.value, x.line))
        
        output = ["❌ Errores encontrados:"]
        
        # Procesar errores por tipo
        for error_type in ErrorType:
            type_errors = [e for e in unique_errors_list if e.type == error_type]
            if type_errors:
                output.append(f"\n{error_type.name}:")
                for error in type_errors:
                    output.append(f"  Línea {error.line}: {error.message}")
                    output.append(f"  En el código:")
                    output.append(f"      {error.code_line}")
                    output.append(f"      {' ' * error.column}^ Aquí")
                    if error.suggestion:
                        output.append(f"  Sugerencia: {error.suggestion}")
        
        # Agregar consejos para errores comunes (solo una vez)
        if any(e.type == ErrorType.SEMANTIC and "función" in e.message.lower() for e in unique_errors_list):
            output.append("\nConsejo: Asegúrate de que todas las funciones que usas estén definidas antes de llamarlas.")
            self.function_advice_added = True
        
        return "\n".join(output)

# Singleton para el manejador de errores
error_handler = ErrorHandler() 