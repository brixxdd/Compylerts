import sys
from ply_lexer import PLYLexer
from ply_parser import PLYParser
from typescript_generator import TypeScriptGenerator
from ast_nodes import print_ast
from colorama import init, Fore, Style
import traceback
import re
from error_handler import error_handler, CompilerError, ErrorType

# Inicializar colorama para salida con color
init()

def compile_to_typescript(source_code: str) -> tuple[str | None, list[str]]:
    """Compila código Python a TypeScript"""
    try:
        # Limpiar errores previos
        error_handler.clear_errors()
        
        # Crear el lexer y parser
        lexer = PLYLexer(source_code)
        
        # Procesar todos los tokens para detectar errores léxicos
        tokens = []
        while True:
            token = lexer.token()
            if not token:
                break
            tokens.append(token)
        
        # Nota: No detenemos el proceso aquí, seguimos para detectar también errores semánticos
        has_lexical_errors = error_handler.get_errors_by_type(ErrorType.LEXICAL)
        
        parser = PLYParser(source_code)
        
        # Pre-registrar todas las funciones definidas en el código
        # Este paso es esencial para evitar falsos errores de "función no definida"
        function_defs = {}
        defined_functions = set()
        for i, line in enumerate(source_code.splitlines(), 1):
            stripped_line = line.strip()
            if stripped_line.startswith('def '):
                try:
                    # Extraer el nombre de la función
                    func_name = stripped_line.split()[1].split('(')[0]
                    # Registrar la función y su línea
                    function_defs[func_name] = i
                    defined_functions.add(func_name)
                    # Añadir a las listas del parser
                    parser.user_defined_functions.add(func_name)
                    if func_name not in parser.known_functions:
                        parser.known_functions.append(func_name)
                    parser.function_contexts.append(func_name)
                except:
                    pass
                    
        # Verificar si hay comas sueltas en el código (trailing commas)
        # Esta es una verificación adicional específica para este error común
        for i, line in enumerate(source_code.splitlines(), 1):
            if '(' in line and ')' in line and ',' in line:
                # Ignorar comentarios
                if '#' in line:
                    line = line.split('#')[0]
                    
                func_start = line.find('(')
                func_end = line.rfind(')')
                if func_start < func_end:
                    args_str = line[func_start+1:func_end]
                    # Verificar coma al final de los argumentos
                    if args_str.strip().endswith(','):
                        # Encontrar la posición de la coma
                        comma_pos = line.rfind(',', func_start, func_end)
                        error_handler.add_error(CompilerError(
                            type=ErrorType.SYNTACTIC,
                            line=i,
                            message="Coma suelta en argumentos de función",
                            code_line=line,
                            column=comma_pos,
                            suggestion="Elimina la coma o añade otro argumento después de la coma"
                        ))
        
        # Remover errores de funciones que en realidad están definidas
        error_handler.remove_function_errors(defined_functions)
        
        # Verificar si es código con estructuras de control
        has_control_structures = False
        if re.search(r'\b(if|for|while)\b.*:', source_code) or 'else:' in source_code:
            has_control_structures = True
        
        # Verificar si hay definiciones de funciones
        has_functions = 'def ' in source_code
        if has_functions:
            parser.indent_level = 4
        
        if has_control_structures and not has_lexical_errors:
            # Usar la conversión directa para estructuras de control
            typescript_code = convert_control_structures(source_code)
            return typescript_code, []
        
        # Parsear el código incluso si hay errores léxicos
        new_lexer = PLYLexer(source_code)
        try:
            ast = parser.parse(source_code, new_lexer)
        except Exception as e:
            # Si falla el parser, continuamos con los errores ya detectados
            ast = None
        
        # Ahora sí, si hay errores, retornarlos
        if error_handler.has_errors():
            return None, [error_handler.format_errors()]
        
        if ast:
            # Generación de código TypeScript
            generator = TypeScriptGenerator()
            typescript_code = generator.generate(ast)
            return typescript_code, []
        else:
            # Convertir directamente a TypeScript sin AST
            if has_control_structures:
                pass
            else:
                typescript_code = convert_simple_expressions(source_code)
                if typescript_code:
                    return typescript_code, []
            
            return None, [error_handler.format_errors()]
            
    except Exception as e:
        error_handler.add_error(CompilerError(
            type=ErrorType.SEMANTIC,
            line=1,
            message=f"Error inesperado: {str(e)}",
            code_line=source_code.splitlines()[0] if source_code else "",
            column=0,
            suggestion="Contacta al desarrollador para reportar este error"
        ))
        return None, [error_handler.format_errors()]

def convert_control_structures(source_code: str) -> str:
    """Convierte estructuras de control de Python a TypeScript usando reemplazos directos por patrones"""
    # Enfoque más sencillo basado en reemplazos directos de cadenas
    
    # Reemplazar palabras clave de Python con sus equivalentes TypeScript
    ts_code = source_code
    
    # Primero manejamos los comentarios para no modificarlos
    lines = ts_code.splitlines()
    output_lines = []
    in_multiline_comment = False
    
    for line in lines:
        stripped = line.strip()
        
        # Manejar líneas vacías y comentarios
        if not stripped or stripped.startswith('#'):
            output_lines.append(line)
            continue
        
        # Manejar indentación 
        indent = len(line) - len(line.lstrip())
        indent_str = ' ' * indent
        
        # Para asignaciones
        if '=' in stripped and not any(stripped.startswith(prefix) for prefix in ['if ', 'for ', 'while ', 'elif ']):
            # Detectar si es una reasignación o una nueva variable
            var_name = stripped.split('=')[0].strip()
            if var_name.lower() not in ['true', 'false', 'null', 'undefined']:
                # Agregar 'let' antes de la primera asignación
                output_lines.append(f"{indent_str}let {stripped};")
            else:
                output_lines.append(f"{indent_str}{stripped};")
        
        # Para print
        elif stripped.startswith('print('):
            # Extraer argumentos de print correctamente
            try:
                open_paren = stripped.index('(')
                args = ''
                # Encontrar el paréntesis de cierre correspondiente
                paren_level = 0
                for i, char in enumerate(stripped[open_paren:]):
                    if char == '(':
                        paren_level += 1
                    elif char == ')':
                        paren_level -= 1
                        if paren_level == 0:
                            args = stripped[open_paren + 1:open_paren + i]
                            break
                
                output_lines.append(f"{indent_str}console.log({args});")
            except:
                # Si hay un error en el análisis, usar una simplificación
                args = stripped[6:-1] if stripped.endswith(')') else stripped[6:]
                output_lines.append(f"{indent_str}console.log({args});")
        
        # Para if
        elif stripped.startswith('if ') and stripped.endswith(':'):
            condition = stripped[3:-1].strip()
            # Convertir operadores lógicos a JavaScript
            condition = condition.replace(' and ', ' && ').replace(' or ', ' || ').replace(' not ', ' ! ')
            output_lines.append(f"{indent_str}if ({condition}) {{")
        
        # Para else
        elif stripped == 'else:':
            output_lines.append(f"{indent_str}}} else {{")
        
        # Para for
        elif stripped.startswith('for ') and ' in ' in stripped and stripped.endswith(':'):
            # Extraer variable y colección
            var_parts = stripped.split(' in ')
            var_name = var_parts[0][4:].strip()  # Quitar "for "
            collection = var_parts[1][:-1].strip()  # Quitar ":"
            output_lines.append(f"{indent_str}for (const {var_name} of {collection}) {{")
        
        # Para while
        elif stripped.startswith('while ') and stripped.endswith(':'):
            condition = stripped[6:-1].strip()
            # Reemplazar len() por .length
            condition = condition.replace('len(', '').replace(')', '.length')
            condition = condition.replace(' and ', ' && ').replace(' or ', ' || ').replace(' not ', ' ! ')
            output_lines.append(f"{indent_str}while ({condition}) {{")
        
        # Para expresiones aritméticas
        elif any(op in stripped for op in ['+', '-', '*', '/', '%']):
            if '=' in stripped:
                output_lines.append(f"{indent_str}{stripped};")
            else:
                output_lines.append(f"{indent_str}{stripped};")
        
        # Otros casos
        else:
            output_lines.append(line)
    
    # Identificar los bloques y agregar llaves de cierre
    processed_lines = []
    pending_blocks = []
    
    i = 0
    while i < len(output_lines):
        line = output_lines[i]
        
        # Agregar la línea actual
        processed_lines.append(line)
        
        # Detectar bloques
        if line.strip().endswith('{'):
            # Es una apertura de bloque, registrar su nivel de indentación
            indent = len(line) - len(line.lstrip())
            pending_blocks.append((indent, i))
        
        # Si hay bloques pendientes, verificar si el siguiente tiene menor indentación
        if pending_blocks and i + 1 < len(output_lines):
            next_line = output_lines[i + 1]
            if next_line.strip() and not next_line.strip().startswith('#'):
                next_indent = len(next_line) - len(next_line.lstrip())
                # Cerrar bloques de mayor indentación
                while pending_blocks and next_indent <= pending_blocks[-1][0]:
                    block_indent, _ = pending_blocks.pop()
                    indent_str = ' ' * block_indent
                    processed_lines.append(f"{indent_str}}}")
        
        i += 1
    
    # Cerrar bloques restantes
    while pending_blocks:
        block_indent, _ = pending_blocks.pop()
        indent_str = ' ' * block_indent
        processed_lines.append(f"{indent_str}}}")
    
    return '\n'.join(processed_lines)

def convert_simple_expressions(source_code: str) -> str:
    """Convierte expresiones simples de Python a TypeScript"""
    lines = source_code.splitlines()
    typescript_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        # Ignorar comentarios y líneas vacías
        if not stripped or stripped.startswith('#'):
            typescript_lines.append(line)
            continue
            
        # Detectar asignación
        if '=' in stripped:
            var_name, value = stripped.split('=', 1)
            typescript_lines.append(f"let {var_name.strip()} = {value.strip()};")
        
        # Detectar print
        elif stripped.startswith('print(') and stripped.endswith(')'):
            args = stripped[6:-1]
            typescript_lines.append(f"console.log({args});")
        
        # Otros casos
        else:
            typescript_lines.append(line)
    
    return '\n'.join(typescript_lines)

def convert_simple_function(source_code: str) -> str:
    """Convierte definiciones de funciones simples de Python a TypeScript"""
    lines = source_code.splitlines()
    ts_lines = []
    
    # Verificar si hay errores de coma suelta
    for i, line in enumerate(lines):
        if '(' in line and ')' in line and ',' in line:
            # Posible llamada a función con argumentos
            open_paren_idx = line.index('(')
            close_paren_idx = line.rindex(')')
            if open_paren_idx < close_paren_idx:
                args_str = line[open_paren_idx+1:close_paren_idx]
                # Verificar coma suelta al final de los argumentos
                if args_str.strip().endswith(','):
                    # Error: hay una coma suelta
                    print(f"""Error sintáctico en línea {i+1}: Coma suelta en argumentos de función
En el código:
    {line}
    {' ' * (line.rindex(',', open_paren_idx, close_paren_idx) + 1)}^ No se permite una coma seguida de paréntesis de cierre
Sugerencia: Elimina la coma o añade otro argumento después de la coma.""")
                    # Devolver None para indicar error y detener la compilación
                    return None
                
                # Verificar comas consecutivas en los argumentos
                parts = args_str.split(',')
                for j in range(len(parts) - 1):
                    if parts[j].strip() == '' and parts[j+1].strip() == '':
                        comma_position = open_paren_idx + 1 + args_str.find(',,')
                        print(f"""Error sintáctico en línea {i+1}: Comas consecutivas en argumentos de función
En el código:
    {line}
    {' ' * comma_position}^ No se permiten comas consecutivas
Sugerencia: Elimina una de las comas o añade un argumento entre ellas.""")
                        return None
                    
                # Verificar si hay argumentos vacíos (ejemplo: func(arg1, , arg2))
                for j, part in enumerate(parts):
                    if part.strip() == '' and j > 0 and j < len(parts) - 1:
                        # Calcular la posición aproximada de la coma problemática
                        pos = 0
                        for k in range(j):
                            pos += len(parts[k]) + 1  # +1 por la coma
                        comma_position = open_paren_idx + 1 + pos
                        print(f"""Error sintáctico en línea {i+1}: Argumento vacío en llamada a función
En el código:
    {line}
    {' ' * comma_position}^ Se esperaba un argumento aquí
Sugerencia: Elimina la coma extra o añade un argumento válido.""")
                        return None
    
    in_function_def = False
    function_indent = 0
    
    # Mapeo de tipos Python a TypeScript
    type_mapping = {
        'int': 'number',
        'str': 'string',
        'float': 'number',
        'bool': 'boolean',
        'list': 'any[]',
        'dict': 'Record<string, any>',
        'None': 'void'
    }
    
    for line in lines:
        # Manejar líneas vacías y comentarios
        if not line.strip():
            ts_lines.append(line)
            continue
        elif line.strip().startswith('#'):
            # Si no estamos dentro de una función, mantener el comentario
            if not in_function_def:
                ts_lines.append(line)
            continue
            
        if line.strip().startswith('def '):
            # Definición de función
            in_function_def = True
            function_indent = len(line) - len(line.lstrip())
            
            # Extraer nombre de la función, parámetros y tipo de retorno
            parts = line.strip().split('(')
            func_name = parts[0].split()[1]
            
            params_and_return = parts[1].split(')')
            params_str = params_and_return[0]
            
            # Procesar parámetros
            params = []
            if params_str.strip():
                for param in params_str.split(','):
                    param = param.strip()
                    if ':' in param:
                        param_name, param_type = param.split(':')
                        param_name = param_name.strip()
                        param_type = param_type.strip()
                        ts_type = type_mapping.get(param_type, 'any')
                        params.append(f"{param_name}: {ts_type}")
                    else:
                        params.append(f"{param}: any")
            
            # Procesar tipo de retorno
            return_type = 'void'
            if '->' in params_and_return[1]:
                return_type_str = params_and_return[1].split('->')[1].strip().split(':')[0].strip()
                return_type = type_mapping.get(return_type_str, 'any')
            
            # Construir declaración de función TypeScript
            ts_lines.append(f"function {func_name}({', '.join(params)}): {return_type} {{")
            
        elif in_function_def:
            # Contenido de la función
            line_indent = len(line) - len(line.lstrip())
            
            if line_indent <= function_indent and line.strip():
                # Salimos de la función
                ts_lines.append('}')
                in_function_def = False
                
                # Procesar esta línea de nuevo, ya no estamos en la función
                if 'print(' in line:
                    # Convertir print a console.log
                    indentation = ' ' * line_indent
                    args = line.strip()[line.strip().index('(')+1:line.strip().rindex(')')]
                    ts_lines.append(f"{indentation}console.log({args});")
                elif '=' in line and not any(line.strip().startswith(x) for x in ['if ', 'for ', 'while ']):
                    # Asignación de variable
                    indentation = ' ' * line_indent
                    ts_lines.append(f"{indentation}let {line.strip()};")
                else:
                    ts_lines.append(line)
            else:
                # Dentro de la función
                if 'return ' in line:
                    # Declaración return
                    indentation = ' ' * line_indent
                    return_expr = line.strip()[7:]  # Quitar "return "
                    ts_lines.append(f"{indentation}return {return_expr};")
                elif 'print(' in line:
                    # Convertir print a console.log
                    indentation = ' ' * line_indent
                    args = line.strip()[line.strip().index('(')+1:line.strip().rindex(')')]
                    ts_lines.append(f"{indentation}console.log({args});")
                elif '=' in line and not any(line.strip().startswith(x) for x in ['if ', 'for ', 'while ']):
                    # Asignación de variable
                    indentation = ' ' * line_indent
                    ts_lines.append(f"{indentation}let {line.strip()};")
                else:
                    ts_lines.append(line)
        else:
            # Fuera de cualquier función
            if 'print(' in line:
                # Convertir print a console.log
                indentation = ' ' * (len(line) - len(line.lstrip()))
                args = line.strip()[line.strip().index('(')+1:line.strip().rindex(')')]
                ts_lines.append(f"{indentation}console.log({args});")
            elif '=' in line and not any(line.strip().startswith(x) for x in ['if ', 'for ', 'while ']):
                # Asignación de variable
                indentation = ' ' * (len(line) - len(line.lstrip()))
                ts_lines.append(f"{indentation}let {line.strip()};")
            else:
                ts_lines.append(line)
    
    # Cerrar la última función si es necesario
    if in_function_def:
        ts_lines.append('}')
    
    return '\n'.join(ts_lines)

def main():
    print("=== Compilador Python a TypeScript ===")
    print("Ingresa tu código Python (presiona Ctrl+D en Linux/Mac o Ctrl+Z en Windows para finalizar):")
    print("-" * 80)
    
    # Leer el código fuente
    try:
        source_code = ""
        while True:
            try:
                line = input()
                source_code += line + "\n"
            except EOFError:
                break
            except KeyboardInterrupt:
                print("\nCompilación cancelada")
                return
    except Exception as e:
        print(f"\n❌ Error al leer el código: {str(e)}")
        return
    
    # Verificar si el código incluye definiciones de funciones
    has_functions = 'def ' in source_code
    
    # Compilar el código
    typescript_code, errors = compile_to_typescript(source_code)
    
    # Mostrar errores si los hay
    if errors:
        print("\n❌ Errores encontrados:")
        for error in errors:
            print(error)
            
        # Sugerencias específicas para errores comunes
        num_strings_unclosed = sum(1 for error in errors if "String sin cerrar" in error)
        num_missing_commas = sum(1 for error in errors if "Falta una coma" in error)
        num_return_errors = sum(1 for error in errors if "return" in error and "función" in error)
        num_undefined_funcs = sum(1 for error in errors if "Función" in error and "no está definida" in error)
        
        if num_strings_unclosed > 0:
            print("\nConsejo: Asegúrate de cerrar todas las cadenas de texto con el mismo tipo de comillas con que las abriste.")
        
        if num_missing_commas > 0:
            print("\nConsejo: Revisa si hay elementos consecutivos que requieren una coma entre ellos, como en listas y diccionarios.")
        
        if num_return_errors > 0:
            print("\nConsejo: Las sentencias 'return' solo pueden aparecer dentro de funciones.")
            
        if num_undefined_funcs > 0:
            print("\nConsejo: Asegúrate de que todas las funciones que usas estén definidas antes de llamarlas.")
            
        return
    
    # Mostrar el código TypeScript generado
    print("\n✅ Compilación exitosa\n")
    print("Código TypeScript generado:")
    print("-" * 40)
    print(typescript_code)

if __name__ == "__main__":
    main()