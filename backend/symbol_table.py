from dataclasses import dataclass
from typing import Dict, Optional, List, Any

@dataclass
class Symbol:
    """Representa un símbolo en la tabla (variable, función, etc)"""
    name: str
    type: str
    kind: str  # 'variable', 'function', 'parameter'
    value: Any = None
    parameters: List['Symbol'] = None  # Para funciones
    return_type: Optional[str] = None  # Para funciones

class Scope:
    """Representa un ámbito (global, función, bloque, etc)"""
    def __init__(self, parent=None, scope_type="block"):
        self.symbols: Dict[str, Symbol] = {}
        self.parent: Optional[Scope] = parent
        self.scope_type = scope_type
        self.children: List[Scope] = []

    def define(self, symbol: Symbol) -> bool:
        """Define un nuevo símbolo en el ámbito actual"""
        if symbol.name in self.symbols:
            return False  # Error: símbolo ya definido
        self.symbols[symbol.name] = symbol
        return True

    def resolve(self, name: str) -> Optional[Symbol]:
        """Busca un símbolo en este ámbito y en los ámbitos padres"""
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.resolve(name)
        return None

class SymbolTable:
    """Tabla de símbolos principal"""
    def __init__(self):
        self.current_scope: Scope = Scope(scope_type="global")
        self.global_scope: Scope = self.current_scope
        self.errors = []  # Para rastrear errores semánticos
        
        # Definir tipos y funciones built-in
        self._define_builtins()

    def _define_builtins(self):
        """Define tipos y funciones built-in de Python"""
        builtins = [
            Symbol("int", "type", "function", parameters=[], return_type="int"),
            Symbol("str", "type", "function", parameters=[], return_type="str"),
            Symbol("float", "type", "function", parameters=[], return_type="float"),
            Symbol("bool", "type", "function", parameters=[], return_type="bool"),
            Symbol("print", "function", "function", parameters=[
                Symbol("value", "any", "parameter")
            ], return_type="None"),
            Symbol("input", "function", "function", parameters=[
                Symbol("prompt", "str", "parameter")
            ], return_type="str"),
            Symbol("len", "function", "function", parameters=[
                Symbol("obj", "any", "parameter")
            ], return_type="int"),
        ]
        for builtin in builtins:
            self.global_scope.define(builtin)

    def enter_scope(self, scope_type="block") -> Scope:
        """Entra en un nuevo ámbito"""
        new_scope = Scope(self.current_scope, scope_type)
        self.current_scope.children.append(new_scope)
        self.current_scope = new_scope
        return new_scope

    def exit_scope(self):
        """Sale del ámbito actual y vuelve al ámbito padre"""
        if self.current_scope.parent:
            self.current_scope = self.current_scope.parent

    def define(self, symbol: Symbol) -> bool:
        """Define un nuevo símbolo en el ámbito actual"""
        # Si es una función, siempre definirla en el ámbito global
        if symbol.kind == 'function':
            if symbol.name in self.global_scope.symbols:
                self.errors.append(
                    f"Error semántico: La función '{symbol.name}' ya está definida"
                )
                return False
            self.global_scope.symbols[symbol.name] = symbol
            return True
        
        # Para otros símbolos, usar el ámbito actual
        if symbol.name in self.current_scope.symbols:
            self.errors.append(
                f"Error semántico: La variable '{symbol.name}' ya está definida en este ámbito"
            )
            return False
        
        self.current_scope.symbols[symbol.name] = symbol
        return True

    def resolve(self, name: str) -> Optional[Symbol]:
        """Busca un símbolo en todos los ámbitos accesibles"""
        return self.current_scope.resolve(name)

    def is_function_scope(self) -> bool:
        """Verifica si el ámbito actual es una función"""
        return self.current_scope.scope_type == "function"

    def check_function_call(self, func_name: str, args: list, line: int) -> bool:
        """Verifica una llamada a función"""
        symbol = self.resolve(func_name)
        if not symbol:
            self.errors.append(
                f"Error semántico en línea {line}: "
                f"La función '{func_name}' no está definida"
            )
            return False
        
        if symbol.kind != "function":
            self.errors.append(
                f"Error semántico en línea {line}: "
                f"'{func_name}' no es una función"
            )
            return False
        
        expected_args = len(symbol.parameters) if symbol.parameters else 0
        if len(args) != expected_args:
            self.errors.append(
                f"Error semántico en línea {line}: "
                f"La función '{func_name}' espera {expected_args} argumentos "
                f"pero recibió {len(args)}"
            )
            return False
        return True

    def check_variable_access(self, var_name: str, line: int) -> bool:
        """Verifica el acceso a una variable"""
        symbol = self.resolve(var_name)
        if not symbol and var_name not in ['True', 'False', 'None']:  # Permitir constantes built-in
            self.errors.append(
                f"Error semántico en línea {line}: "
                f"Variable '{var_name}' no está definida"
            )
            return False
        return True 