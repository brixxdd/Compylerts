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
        # Crear instancia del lexer y parser
        lexer = PLYLexer(request.code)
        parser = PLYParser()
        
        # Preparar respuesta
        response = {
            "success": True,
            "output": [],  # Aquí guardaremos el output formateado
            "errors": []
        }
        
        # Recolectar tokens y formatearlos como en la terminal
        response["output"].append("Tokens encontrados:")
        response["output"].append("----------------------------------------")
        
        while True:
            tok = lexer.token()
            if not tok:
                break
            # Formatear cada token como en la terminal
            token_line = f"{tok.type}: {str(tok.value)}"
            response["output"].append(token_line)
        
        # Realizar el análisis
        result = parser.parse(request.code)
        
        # Añadir errores si existen
        if parser.errors:
            response["success"] = False
            response["errors"].extend(parser.errors)
        else:
            response["output"].append("\n✅ No se encontraron errores")
            response["output"].append("✅ Análisis completado sin errores")
        
        if parser.semantic_errors:
            response["success"] = False
            response["errors"].extend(parser.semantic_errors)
        
        return response
        
    except Exception as e:
        return {
            "success": False,
            "errors": [str(e)],
            "output": []
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 