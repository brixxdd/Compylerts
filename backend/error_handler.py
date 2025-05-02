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

class ErrorHandler:
    def __init__(self):
        self.errors: List[CompilerError] = []
        
    def add_error(self, error: CompilerError):
        self.errors.append(error)
    
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    def get_errors_by_type(self, error_type: ErrorType) -> List[CompilerError]:
        return [e for e in self.errors if e.type == error_type]
    
    def format_errors(self) -> str:
        if not self.errors:
            return ""
        
        # Ordenar errores primero por tipo y luego por línea
        self.errors.sort(key=lambda x: (x.type.value, x.line))
        
        output = ["❌ Errores encontrados:"]
        
        # Procesar errores por tipo
        for error_type in ErrorType:
            type_errors = self.get_errors_by_type(error_type)
            if type_errors:
                output.append(f"\n{error_type.name}:")
                for error in type_errors:
                    output.append(f"  Línea {error.line}: {error.message}")
                    output.append(f"  En el código:")
                    output.append(f"      {error.code_line}")
                    output.append(f"      {' ' * error.column}^ Aquí")
                    if error.suggestion:
                        output.append(f"  Sugerencia: {error.suggestion}")
        
        return "\n".join(output)

# Singleton para el manejador de errores
error_handler = ErrorHandler() 