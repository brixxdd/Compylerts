import React, { useState, useRef, JSX } from 'react'
import { CompileResponse } from '../App'
import './Terminal.css'

interface TerminalProps {
  code: string
  result: CompileResponse | null
  loading: boolean
}

function Terminal({ code, result, loading }: TerminalProps) {
  const [activeTab, setActiveTab] = useState<'output' | 'typescript'>('output');

  // Función para formatear la salida de la compilación
  const formatOutput = (output: string[] | undefined): JSX.Element[] => {
    if (!output || output.length === 0) {
      return [<div key="no-output">No hay salida disponible</div>];
    }

    return output.map((line, index) => {
      // Colorear errores
      if (line.includes('Error') && (line.includes('léxico') || line.includes('sintáctico') || line.includes('semántico'))) {
        return <div key={index} className="terminal-line error-text">{line}</div>;
      }
      // Colorear mensajes de éxito
      else if (line.includes('✅')) {
        return <div key={index} className="terminal-line success-line">{line}</div>;
      }
      // Formatear líneas normales
      else {
        return <div key={index} className="terminal-line">{line}</div>;
      }
    });
  };

  // Función para dar formato al código TypeScript
  const formatTypescript = (code: string): string => {
    if (!code) return '';
    
    // Aplicar indentación consistente
    const lines = code.split('\n');
    let indentLevel = 0;
    let formattedLines = [];

    for (let line of lines) {
      const trimmedLine = line.trim();
      
      // Ajustar nivel de indentación
      if (trimmedLine.endsWith('}') && indentLevel > 0) {
        indentLevel--;
      }
      
      // Añadir la línea con la indentación correcta
      formattedLines.push('  '.repeat(indentLevel) + trimmedLine);
      
      // Incrementar indentación si la línea abre un bloque
      if (trimmedLine.endsWith('{')) {
        indentLevel++;
      }
    }
    
    return formattedLines.join('\n');
  };

  // Función para descargar el código TypeScript
  const handleDownload = () => {
    if (!result?.typescript_code) return;
    
    const formattedCode = formatTypescript(result.typescript_code);
    const blob = new Blob([formattedCode], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = 'codigo_generado.ts';
    document.body.appendChild(a);
    a.click();
    
    // Limpiar
    setTimeout(() => {
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 100);
  };

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
      
      <div className="terminal-tabs">
        <button 
          className={`terminal-tab ${activeTab === 'output' ? 'active' : ''}`}
          onClick={() => setActiveTab('output')}
        >
          Salida
        </button>
        <button 
          className={`terminal-tab ${activeTab === 'typescript' ? 'active' : ''}`}
          onClick={() => setActiveTab('typescript')}
        >
          TypeScript
        </button>
      </div>
      
      {activeTab === 'output' && (
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
              {/* Mostrar la salida del compilador tal como lo hace main.py */}
              {result.output && result.output.length > 0 ? (
                formatOutput(result.output)
              ) : null}
              
              {/* Mostrar errores si los hay */}
              {result.errors.length > 0 && (
                <>
                  {/* Encabezado unificado para errores */}
                  <div className="terminal-line error-text">
                    ❌ Errores encontrados:
                  </div>
                  
                  {result.errors.map((error, idx) => (
                    <div key={`err-${idx}`} className="error-message">
                      {error.split('\n').map((line, i) => (
                        <div key={i}>{line}</div>
                      ))}
                    </div>
                  ))}
                </>
              )}

              {/* Mostrar mensaje de éxito si no hay errores */}
              {result.success && result.errors.length === 0 && !result.output.find(line => line.includes('✅')) && (
                <>
                  <div className="terminal-line success-line">✅ No se encontraron errores</div>
                  <div className="terminal-line success-line">✅ Análisis completado sin errores</div>
                </>
              )}
            </>
          ) : (
            <div className="terminal-line">
              // Esperando código para analizar...
            </div>
          )}
        </div>
      )}
      
      {activeTab === 'typescript' && (
        <div className="terminal-content">
          <div className="terminal-line">
            === Código TypeScript Generado ===
          </div>
          <div className="terminal-line">
            --------------------------------------------------------------------------------
          </div>
          
          {loading ? (
            <div className="terminal-line">Generando código TypeScript...</div>
          ) : result ? (
            <>
              {result.errors.length > 0 ? (
                <div className="terminal-line error-text">
                  No se pudo generar código TypeScript debido a errores en el código fuente.
                </div>
              ) : (
                <>
                  {/* Botón para descargar el código TypeScript */}
                  {result.typescript_code && (
                    <div className="download-button-container">
                      <button 
                        onClick={handleDownload}
                        className="download-button"
                      >
                        <span className="download-icon">⬇️</span> Descargar código TypeScript
                      </button>
                    </div>
                  )}
                  
                  <div className="ts-container">
                    <div className="ts-code-section">
                      {/* Mostrar código TypeScript */}
                      <div className="terminal-line">
                        <strong>Código:</strong>
                      </div>
                      <pre className="typescript-code">
                        {formatTypescript(result.typescript_code || 'No se generó código TypeScript.')}
                      </pre>
                    </div>
                    
                    <div className="ts-info-section">
                      {/* Mostrar tipos inferidos */}
                      {result.inferred_types && Object.keys(result.inferred_types).length > 0 && (
                        <div className="inferred-types-section">
                          <div className="terminal-line">
                            <strong>Tipos Inferidos:</strong>
                          </div>
                          <table className="types-table">
                            <thead>
                              <tr>
                                <th>Variable</th>
                                <th>Tipo</th>
                              </tr>
                            </thead>
                            <tbody>
                              {Object.entries(result.inferred_types || {}).map(([varName, varType], index) => (
                                <tr key={index}>
                                  <td>{varName}</td>
                                  <td>{varType}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  </div>
                </>
              )}
            </>
          ) : (
            <div className="terminal-line">
              // Esperando código para compilar...
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default Terminal