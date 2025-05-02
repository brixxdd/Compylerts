from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ply_lexer import PLYLexer
from ply_parser import PLYParser
from typescript_generator import TypeScriptGenerator
from main import compile_to_typescript
from error_handler import error_handler, ErrorType
import re
import sys
import io

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

        # Resetear errores previos
        error_handler.errors = []

        # Capturar la salida de la compilación
        old_stdout = sys.stdout
        redirected_output = io.StringIO()
        sys.stdout = redirected_output

        # PRIMERA FASE: Detección de errores léxicos
        lexer = PLYLexer(code)
        tokens = []
        while True:
            token = lexer.token()
            if not token:
                break
            tokens.append(token)
        
        # SEGUNDA FASE: Detección de errores semánticos y sintácticos
        # incluso si ya hay errores léxicos
        parser = PLYParser(code)
        try:
            # Pre-registrar todas las funciones definidas en el código
            for i, line in enumerate(code.splitlines()):
                stripped_line = line.strip()
                if stripped_line.startswith('def '):
                    try:
                        func_name = stripped_line.split()[1].split('(')[0]
                        parser.user_defined_functions.add(func_name)
                        parser.known_functions.append(func_name)
                        parser.function_contexts.append(func_name)
                    except:
                        pass
            
            # Intentar parsear el código incluso con errores léxicos
            ast = parser.parse(code, PLYLexer(code))
        except Exception as e:
            # Si falla el parser, continuamos con los errores ya detectados
            print(f"DEBUG: Exception during parsing: {str(e)}")
        
        # TERCERA FASE (opcional): Intentar compilar a TypeScript
        # Solo lo hacemos si no hay errores léxicos graves
        has_lexical_errors = any(err.type == ErrorType.LEXICAL for err in error_handler.errors)
        if not has_lexical_errors:
            try:
                typescript_code, errors = compile_to_typescript(code)
            except Exception as e:
                typescript_code = None
                errors = [str(e)]
                print(f"DEBUG: Exception during TypeScript compilation: {str(e)}")
        else:
            typescript_code = None
            errors = []
        
        # Restaurar stdout
        sys.stdout = old_stdout
        
        # Obtener la salida capturada
        output_text = redirected_output.getvalue()
        output_lines = output_text.splitlines()
        
        # Filtrar líneas de DEBUG si es necesario
        filtered_output = [line for line in output_lines if not line.startswith("DEBUG")]

        # Obtener errores formateados directamente del error_handler
        formatted_errors = []
        if error_handler.has_errors():
            formatted_errors = [error_handler.format_errors()]

        # Determinar la fase del error basada en los tipos de errores presentes
        phase = "success"
        if error_handler.has_errors():
            lexical_errors = error_handler.get_errors_by_type(ErrorType.LEXICAL)
            syntactic_errors = error_handler.get_errors_by_type(ErrorType.SYNTACTIC)
            semantic_errors = error_handler.get_errors_by_type(ErrorType.SEMANTIC)
            
            if lexical_errors:
                phase = "lexical"
            elif syntactic_errors:
                phase = "syntactic"
            elif semantic_errors:
                phase = "semantic"
            else:
                phase = "error"
        
        # Errores por tipo para el frontend
        grouped_errors = {
            "lexical": [error for error in error_handler.errors if error.type == ErrorType.LEXICAL],
            "syntactic": [error for error in error_handler.errors if error.type == ErrorType.SYNTACTIC],
            "semantic": [error for error in error_handler.errors if error.type == ErrorType.SEMANTIC]
        }

        # Convertir errores a formato JSON
        serialized_errors = {
            error_type: [
                {
                    "line": err.line,
                    "message": err.message,
                    "code_line": err.code_line,
                    "column": err.column,
                    "suggestion": err.suggestion
                } for err in errors_list
            ]
            for error_type, errors_list in grouped_errors.items() if errors_list
        }

        response = {
            "success": not error_handler.has_errors(),
            "output": filtered_output,
            "errors": formatted_errors or errors or [],
            "grouped_errors": serialized_errors,
            "tokens": [],
            "phase": phase,
            "typescript_code": typescript_code or "",
            "raw_error_output": filtered_output if error_handler.has_errors() else []
        }

        # Procesar tokens
        lexer = PLYLexer(code)
        tokens = []
        while True:
            tok = lexer.token()
            if not tok:
                break
            token_info = {
                "type": tok.type,
                "value": str(tok.value),
                "line": tok.lineno,
                "column": tok.lexpos
            }
            tokens.append(token_info)
        
        response["tokens"] = tokens

        # Extraer tipos inferidos si hay código TypeScript
        if typescript_code:
            inferred_types = extract_inferred_types(typescript_code)
            response["inferred_types"] = inferred_types

        return response

    except Exception as e:
        return {
            "success": False,
            "phase": "error",
            "errors": [str(e)],
            "output": ["Error inesperado: " + str(e)],
            "tokens": []
        }

def extract_inferred_types(typescript_code: str) -> dict:
    """Extrae los tipos inferidos de las variables a partir del código TypeScript generado"""
    inferred_types = {}
    
    # Buscar declaraciones de variables con tipos
    pattern = r'let\s+(\w+):\s+(\w+(?:\[\])?)\s*='
    matches = re.findall(pattern, typescript_code)
    
    for var_name, var_type in matches:
        inferred_types[var_name] = var_type
    
    return inferred_types

@app.post("/run-main")
async def run_main(request: CompileRequest):
    try:
        # Asegurar que el código termine con un salto de línea
        code = request.code
        if not code.endswith('\n'):
            code = code + '\n'

        # Capturar la salida de la compilación
        old_stdout = sys.stdout
        redirected_output = io.StringIO()
        sys.stdout = redirected_output

        # Ejecutar el compilador directamente
        typescript_code, errors = compile_to_typescript(code)
        
        # Restaurar stdout
        sys.stdout = old_stdout
        
        # Obtener la salida capturada
        output_text = redirected_output.getvalue()
        
        return {
            "success": not errors,
            "errors": errors or [],
            "typescript_code": typescript_code or "",
            "output": output_text.splitlines()
        }
        
    except Exception as e:
        return {
            "success": False,
            "errors": [str(e)],
            "typescript_code": "",
            "output": ["Error inesperado: " + str(e)]
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 