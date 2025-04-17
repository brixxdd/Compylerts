from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ply_lexer import PLYLexer
from ply_parser import PLYParser

app = FastAPI()

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # URL del frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CompileRequest(BaseModel):
    code: str

@app.post("/compile")
async def compile_code(request: CompileRequest):
    try:
        # Asegurar que el código termine con un salto de línea
        code = request.code
        if not code.endswith('\n'):
            code = code + '\n'

        response = {
            "success": True,
            "output": [],
            "errors": [],
            "tokens": [],
            "phase": "lexical"  # Empezamos con fase léxica
        }

        # Lista para almacenar todos los errores detectados
        all_errors = []
        
        # Fase 1: Análisis Léxico
        lexer = PLYLexer(code)
        
        # Recolectar tokens para mostrarlos
        tokens = []
        while True:
            tok = lexer.token()
            if not tok:
                break
            token_info = {
                "type": tok.type,
                "value": str(tok.value),
                "line": tok.lineno
            }
            tokens.append(token_info)
            response["output"].append(f"{tok.type}: {str(tok.value)}")
        
        response["tokens"] = tokens
        
        # Verificar si hay errores léxicos (incluyendo corchetes sin cerrar)
        if lexer.errors:
            response["success"] = False
            
            # Identificar si hay errores de corchetes
            bracket_errors = [err for err in lexer.errors if "Corchete sin cerrar" in err]
            if bracket_errors:
                response["phase"] = "syntactic"  # Tratar como error sintáctico
                all_errors.extend(bracket_errors)
            else:
                response["phase"] = "lexical"
                all_errors.extend(lexer.errors)
        
        # Añadir verificación específica para corchetes sin cerrar
        bracket_stack = []
        line_number = 1

        for i, char in enumerate(code):
            if char == '[':
                bracket_stack.append((line_number, i))
            elif char == ']' and bracket_stack:
                bracket_stack.pop()
            elif char == '\n':
                line_number += 1

        # Reportar los corchetes sin cerrar
        if bracket_stack:
            response["success"] = False
            response["phase"] = "syntactic"
            
            for line_no, pos in bracket_stack:
                # Calcular la posición en la línea
                lines = code.split('\n')
                if 0 <= line_no - 1 < len(lines):
                    line = lines[line_no - 1]
                    column = pos - sum(len(l) + 1 for l in lines[:line_no - 1])
                    
                    error_msg = f"""Error sintáctico en línea {line_no}: Corchete sin cerrar
En el código:
    {line}
    {' ' * column}^ Falta el corchete de cierre ']'
Sugerencia: {line}]"""
                    
                    all_errors.append(error_msg)
        
        # Fase 2: Análisis Sintáctico y Semántico
        parser = PLYParser()
        result = parser.parse(code)
        
        # Verificar errores sintácticos
        if parser.errors:
            response["success"] = False
            
            # Verificar si hay errores semánticos mezclados con los sintácticos
            semantic_errors = [err for err in parser.errors if "Error semántico" in err]
            syntactic_errors = [err for err in parser.errors if "Error semántico" not in err]
            
            # Agregar errores sintácticos
            if syntactic_errors:
                response["phase"] = "syntactic"
                all_errors.extend(syntactic_errors)
            
            # También agregar los errores semánticos si existen
            if semantic_errors:
                # Eliminar duplicados de errores semánticos
                unique_semantic_errors = []
                for err in semantic_errors:
                    if err not in unique_semantic_errors:
                        unique_semantic_errors.append(err)
                all_errors.extend(unique_semantic_errors)
        
        # Verificar errores semánticos específicos
        if parser.semantic_errors:
            response["success"] = False
            if not all_errors:  # Si no hay otros errores, establecer fase a semántica
                response["phase"] = "semantic"
            
            # Eliminar duplicados entre semantic_errors y all_errors
            unique_semantic_errors = []
            for err in parser.semantic_errors:
                if err not in all_errors and err not in unique_semantic_errors:
                    unique_semantic_errors.append(err)
            
            all_errors.extend(unique_semantic_errors)
        
        # Guardar todos los errores en la respuesta
        response["errors"] = all_errors
        
        # Agregar mensajes de salida según los errores
        if all_errors:
            # Determinar el tipo de encabezado basado en el contenido de los errores
            if any("Error léxico" in err for err in all_errors):
                response["output"].append("❌ Errores léxicos encontrados:")
            elif any("Error sintáctico" in err for err in all_errors):
                response["output"].append("❌ Errores sintácticos encontrados:")
            elif any("Error semántico" in err for err in all_errors):
                response["output"].append("❌ Errores semánticos encontrados:")
            else:
                response["output"].append("❌ Errores encontrados:")
            
            response["output"].extend(all_errors)
        else:
            response["output"].append("✅ No se encontraron errores")
            response["output"].append("✅ Análisis completado sin errores")
        
        return response

    except Exception as e:
        return {
            "success": False,
            "phase": "error",
            "errors": [str(e)],
            "output": [],
            "tokens": []
        }

@app.post("/run-main")
async def run_main(request: CompileRequest):
    try:
        # Asegurar que el código termine con un salto de línea
        code = request.code
        if not code.endswith('\n'):
            code = code + '\n'

        # Simular la ejecución de main.py
        output_lines = [
            "=== Análisis Léxico y Sintáctico con PLY ===",
            "Ingresa tu código (presiona Ctrl+D en Linux/Mac o Ctrl+Z en Windows para finalizar):",
            "--------------------------------------------------------------------------------"
        ]
        
        # Crear instancia del lexer
        lexer = PLYLexer(code)
        
        # Agregar el código ingresado
        output_lines.extend(code.split('\n'))
        output_lines.append("")
        
        # Agregar tokens encontrados
        output_lines.append("Tokens encontrados:")
        output_lines.append("----------------------------------------")
        
        tokens = []
        while True:
            tok = lexer.token()
            if not tok:
                break
            tokens.append(f"{tok.type}: {str(tok.value)}")
        
        output_lines.extend(tokens)
        
        # Agregar errores si existen
        if lexer.errors:
            output_lines.append("")
            output_lines.append("❌ Errores léxicos:")
            output_lines.extend(lexer.errors)
        
        return {
            "success": not lexer.errors,
            "terminal_output": output_lines
        }
        
    except Exception as e:
        return {
            "success": False,
            "terminal_output": [
                "Error inesperado:",
                str(e)
            ]
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 