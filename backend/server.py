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

        # Verificar paréntesis sin cerrar por línea
        lines = code.split('\n')
        for i, line in enumerate(lines):
            parenthesis_stack = []
            for char in line:
                if char == '(':
                    parenthesis_stack.append(char)
                elif char == ')' and parenthesis_stack:
                    parenthesis_stack.pop()
            
            if parenthesis_stack:  # Si quedan paréntesis sin cerrar en esta línea
                line_number = i + 1
                error_msg = f"Error léxico en línea {line_number}: Paréntesis sin cerrar"
                open_paren_pos = line.rfind('(')
                
                response["success"] = False
                response["phase"] = "lexical"
                response["errors"].append(error_msg)
                response["errors"].append(f"En el código:\n    {line}\n    {' ' * open_paren_pos}^ Falta el paréntesis de cierre")
                response["output"].append(f"❌ Error léxico en línea {line_number}:")
                response["output"].append(error_msg)

        # Verificar paréntesis sin cerrar primero (verificación preliminar)
        parenthesis_stack = []
        line_number = 1
        last_open_paren_line = 0
        
        for i, char in enumerate(code):
            if char == '(':
                parenthesis_stack.append((char, line_number))
            elif char == ')' and parenthesis_stack:
                parenthesis_stack.pop()
            elif char == '\n':
                line_number += 1
        
        # Si quedan paréntesis sin cerrar, reportar error específico
        if parenthesis_stack:
            paren_char, paren_line = parenthesis_stack[0]
            error_msg = f"Error sintáctico en línea {paren_line}: Paréntesis sin cerrar '(' que no tiene su correspondiente ')'"
            
            # Encontrar la línea con el paréntesis sin cerrar
            line = code.split('\n')[paren_line - 1]
            
            # Agregar contexto al error
            response["success"] = False
            response["phase"] = "syntactic"
            response["errors"].append(error_msg)
            response["errors"].append(f"En el código:\n    {line}\n    ^ Falta el paréntesis de cierre")
            response["output"].append("❌ Error sintáctico encontrado:")
            response["output"].append(error_msg)
            return response
        
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