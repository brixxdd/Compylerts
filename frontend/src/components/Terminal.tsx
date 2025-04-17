import { useState, useEffect, useRef } from 'react'
import { CompileResponse } from '../App'
import './Terminal.css'

interface TerminalProps {
  code: string
  result: CompileResponse | null
  loading: boolean
}

function Terminal({ code, result, loading }: TerminalProps) {
  return (
    <div className="terminal-window">
      <div className="terminal-header">
        <span className="terminal-title">python3 main.py</span>
        <div className="terminal-buttons">
          <span className="terminal-button minimize"></span>
          <span className="terminal-button maximize"></span>
          <span className="terminal-button close"></span>
        </div>
      </div>
      <div className="terminal-content">
        <div className="terminal-line">
          === Análisis Léxico y Sintáctico con PLY ===
        </div>
        <div className="terminal-line">
          Ingresa tu código (presiona Ctrl+D en Linux/Mac o Ctrl+Z en Windows para finalizar):
        </div>
        <div className="terminal-line">
          --------------------------------------------------------------------------------
        </div>
        
        {/* Mostrar el código */}
        <pre className="terminal-code">{code}</pre>
        
        {loading ? (
          <div className="terminal-line">Analizando...</div>
        ) : result ? (
          <>
            {/* Mostrar solo errores en orden: léxicos -> sintácticos -> semánticos */}
            {result.errors.length > 0 && (
              <>
                {/* Encabezado unificado para errores */}
                <div className="terminal-line error-text">
                  ❌ Errores encontrados:
                </div>
                
                {(() => {
                  // Identificar tipos de errores únicos (sin duplicados)
                  const uniqueErrors = Array.from(new Set(result.errors));
                  
                  // Clasificar errores por tipo
                  const lexicalErrors = uniqueErrors.filter(err => 
                    err.includes("Error léxico") || err.includes("carácter no válido")
                  );
                  
                  const syntacticErrors = uniqueErrors.filter(err => 
                    (err.includes("Error sintáctico") && !err.includes("Error semántico"))
                  );
                  
                  const semanticErrors = uniqueErrors.filter(err => 
                    err.includes("Error semántico")
                  );
                  
                  // Mostrar todos los errores en orden específico
                  return (
                    <>
                      {lexicalErrors.map((error, index) => (
                        <div key={`lex-${index}`} className="terminal-line error-text">
                          {error.split('\n').map((line, i) => (
                            <div key={i}>{line}</div>
                          ))}
                        </div>
                      ))}
                      
                      {syntacticErrors.map((error, index) => (
                        <div key={`syn-${index}`} className="terminal-line error-text">
                          {error.split('\n').map((line, i) => (
                            <div key={i}>{line}</div>
                          ))}
                        </div>
                      ))}
                      
                      {semanticErrors.map((error, index) => (
                        <div key={`sem-${index}`} className="terminal-line error-text">
                          {error.split('\n').map((line, i) => (
                            <div key={i}>{line}</div>
                          ))}
                        </div>
                      ))}
                    </>
                  );
                })()}
              </>
            )}

            {/* Mostrar mensaje de éxito si no hay errores */}
            {result.success && (
              <>
                <div className="terminal-line">✅ No se encontraron errores</div>
                <div className="terminal-line">✅ Análisis completado sin errores</div>
              </>
            )}
          </>
        ) : (
          <div className="terminal-line">
            // Esperando código para analizar...
          </div>
        )}
      </div>
    </div>
  )
}

export default Terminal