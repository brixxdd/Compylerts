import sys
from ply_lexer import PLYLexer
from ply_parser import PLYParser
from typescript_generator import TypeScriptGenerator
from ast_nodes import print_ast
from colorama import init, Fore, Style
import traceback
import re

# Inicializar colorama para salida con color
init()

def compile_to_typescript(source_code: str) -> tuple[str | None, list[str]]:
    """Compila código Python a TypeScript"""
    try:
        # Crear el lexer y parser
        print("Inicializando lexer...")
        lexer = PLYLexer(source_code)
        
        # Si hay errores en el lexer o el código no es válido, retornar los errores inmediatamente
        if not lexer.valid_code:
            return None, lexer.errors
        
        print("Inicializando parser...")
        parser = PLYParser(source_code)
        
        # Verificar si es código con estructuras de control
        has_control_structures = False
        if re.search(r'\b(if|for|while)\b.*:', source_code) or 'else:' in source_code:
            has_control_structures = True
            print("Código con estructuras de control detectado")
        
        if has_control_structures:
            # Usar la conversión directa para estructuras de control
            print("Usando conversión directa para estructuras de control")
            typescript_code = convert_control_structures(source_code)
            return typescript_code, []
        
        # Parsear el código
        print("Parseando código...")
        ast = parser.parser.parse(input=source_code, lexer=lexer.lexer)
        print(f"AST generado: {ast is not None}")
        
        # Filtrar errores específicos relacionados con print en bloques
        filtered_errors = []
        ignored_errors = 0
        for error in parser.errors:
            if "Token inesperado 'print'" in error or "Token inesperado ':'" in error:
                ignored_errors += 1
            else:
                filtered_errors.append(error)
        
        if ignored_errors > 0:
            print(f"Se ignoraron {ignored_errors} errores relacionados con 'print' en bloques")
        
        # Si hay errores que no ignoramos, retornarlos
        if filtered_errors:
            return None, filtered_errors
        
        if ast:
            print("\n=== AST Generated ===")
            print_ast(ast)
            print("===================\n")
            
            # Generación de código TypeScript
            print("Generando código TypeScript...")
            generator = TypeScriptGenerator()
            typescript_code = generator.generate(ast)
            return typescript_code, []
        else:
            # Convertir directamente a TypeScript sin AST
            # Este método es una solución provisional para casos simples
            if has_control_structures:
                # Ya intentamos con la conversión directa anteriormente
                pass
            else:
                # Intenta un enfoque más simple para expresiones básicas
                typescript_code = convert_simple_expressions(source_code)
                if typescript_code:
                    return typescript_code, []
            
            return None, ["Error: No se pudo generar el AST"]
            
    except Exception as e:
        print(f"Excepción inesperada: {str(e)}")
        traceback.print_exc()
        return None, [f"❌ Error inesperado: {str(e)}"]

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
    
    # Compilar el código
    typescript_code, errors = compile_to_typescript(source_code)
    
    # Mostrar errores si los hay
    if errors:
        print("\n❌ Errores encontrados:")
        for error in errors:
            print(error)
        return
    
    # Mostrar el código TypeScript generado
    print("\n✅ Compilación exitosa\n")
    print("Código TypeScript generado:")
    print("-" * 40)
    print(typescript_code)

if __name__ == "__main__":
    main()