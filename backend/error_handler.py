from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional

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
        
    def add_error(self, error: CompilerError):
        # Verificar si este error ya existe (mismo tipo, línea, mensaje, columna)
        for existing_error in self.errors:
            if (existing_error.type == error.type and
                existing_error.line == error.line and
                existing_error.message == error.message and
                existing_error.column == error.column):
                # Error duplicado, no agregarlo
                return
        # Si no es duplicado, agregarlo
        self.errors.append(error)
    
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    def get_errors_by_type(self, error_type: ErrorType) -> List[CompilerError]:
        return [e for e in self.errors if e.type == error_type]
    
    def clear_errors(self):
        """Limpia todos los errores acumulados"""
        self.errors = []
    
    def format_errors(self) -> str:
        if not self.errors:
            return ""
        
        # Ordenar errores primero por tipo y luego por línea
        self.errors.sort(key=lambda x: (x.type.value, x.line))
        
        # Eliminamos cualquier duplicado que haya pasado
        unique_errors = []
        for error in self.errors:
            if error not in unique_errors:
                unique_errors.append(error)
        
        output = ["❌ Errores encontrados:"]
        
        # Procesar errores por tipo
        for error_type in ErrorType:
            type_errors = [e for e in unique_errors if e.type == error_type]
            if type_errors:
                output.append(f"\n{error_type.name}:")
                for error in type_errors:
                    output.append(f"  Línea {error.line}: {error.message}")
                    output.append(f"  En el código:")
                    output.append(f"      {error.code_line}")
                    output.append(f"      {' ' * error.column}^ Aquí")
                    if error.suggestion:
                        output.append(f"  Sugerencia: {error.suggestion}")
        
        # Agregar consejos para errores comunes
        if any(e.type == ErrorType.SEMANTIC and "función" in e.message.lower() for e in unique_errors):
            output.append("\nConsejo: Asegúrate de que todas las funciones que usas estén definidas antes de llamarlas.")
        
        return "\n".join(output)

# Singleton para el manejador de errores
error_handler = ErrorHandler() 