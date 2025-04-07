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

        # Fase 1: Análisis Léxico
        lexer = PLYLexer(code)
        
        # Verificar errores léxicos primero
        if not lexer.valid_code or lexer.errors:
            response["success"] = False
            response["phase"] = "lexical"  # Mantener fase léxica si hay errores
            response["errors"] = lexer.errors
            response["output"].append("❌ Errores léxicos encontrados:")
            response["output"].extend(lexer.errors)
            return response

        # Recolectar tokens si no hay errores léxicos
        response["output"].append("Tokens encontrados:")
        response["output"].append("----------------------------------------")
        
        while True:
            tok = lexer.token()
            if not tok:
                break
            token_info = {
                "type": tok.type,
                "value": str(tok.value),
                "line": tok.lineno
            }
            response["tokens"].append(token_info)
            response["output"].append(f"{tok.type}: {str(tok.value)}")

        # Fase 2: Análisis Sintáctico y Semántico
        parser = PLYParser()
        result = parser.parse(code)

        if parser.errors:
            response["success"] = False
            response["phase"] = "syntactic"
            response["errors"].extend(parser.errors)
            response["output"].append("❌ Errores sintácticos encontrados:")
            response["output"].extend(parser.errors)
        elif parser.semantic_errors:
            response["success"] = False
            response["phase"] = "semantic"
            response["errors"].extend(parser.semantic_errors)
            response["output"].append("❌ Errores semánticos encontrados:")
            response["output"].extend(parser.semantic_errors)
        else:
            response["phase"] = "semantic"  # Fase final si todo está bien
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