import { useState } from 'react'
import Editor from '@monaco-editor/react'
import axios from 'axios'
import './App.css'
import Welcome from './components/Welcome'
import Terminal from './components/Terminal'

interface Token {
  type: string
  value: string
  line: number
}

interface InferredTypes {
  [key: string]: string;
}

interface CompilerDetailedError {
  line: number;
  message: string;
  code_line: string;
  column: number;
  suggestion?: string;
}

interface GroupedErrors {
  lexical?: CompilerDetailedError[];
  syntactic?: CompilerDetailedError[];
  semantic?: CompilerDetailedError[];
}

export interface CompileResponse {
  success: boolean
  tokens: Token[]
  errors: string[]
  ast?: any
  output: string[]
  phase: 'lexical' | 'syntactic' | 'semantic' | 'error'
  typescript_code?: string
  inferred_types?: InferredTypes
  raw_error_output?: string[]
  grouped_errors?: GroupedErrors
  analysis?: {
    lexical: { success: boolean, errors: string[], tokens?: Token[] }
    syntactic: { success: boolean, errors: string[] }
    semantic: { success: boolean, errors: string[] }
  }
}

function App() {
  const [showWelcome, setShowWelcome] = useState(true)
  const [code, setCode] = useState<string>(`# Escribe tu código Python aquí
# Ejemplo:
def suma(a, b):
    return a + b

x = 5
y = 10
resultado = suma(x, y)
print(resultado)

# Lista simple de enteros
numeros = [1, 2, 3, 4, 5]
`)
  const [result, setResult] = useState<CompileResponse | null>(null)
  const [loading, setLoading] = useState(false)

  const parseTokensFromOutput = (output: string[]): Token[] => {
    const tokens: Token[] = []
    let currentLine = 1
    
    output.forEach(line => {
      if (line.includes(':')) {
        const [type, value] = line.split(':').map(s => s.trim())
        if (type && !line.includes('----------------------------------------')) {
          tokens.push({
            type: type,
            value: value || '',
            line: currentLine
          })
          if (type === 'NEWLINE') {
            currentLine++
          }
        }
      }
    })
    
    return tokens
  }

  const handleCompile = async () => {
    setLoading(true)
    try {
      const codeWithoutComments = code.replace(/#.*$/gm, '').trim()
      if (!codeWithoutComments) {
        setResult({
          success: false,
          tokens: [],
          errors: ['Por favor, escribe algún código Python para compilar'],
          ast: null,
          output: [],
          phase: 'error',
          analysis: {
            lexical: { success: false, errors: ['Por favor, escribe algún código Python para compilar'] },
            syntactic: { success: false, errors: [] },
            semantic: { success: false, errors: [] }
          }
        })
        setLoading(false)
        return
      }

      // Validación de caracteres especiales
      const invalidCharsRegex = /[@$¿¡]/g
      const invalidChars = code.match(invalidCharsRegex)
      if (invalidChars) {
        const lines = code.split('\n')
        const errors: string[] = []
        
        // Agrupamos los errores por tipo para el mismo formato que el backend
        const lexicalErrors: CompilerDetailedError[] = []
        
        lines.forEach((line, lineIndex) => {
          const invalidCharPositions = [...line.matchAll(invalidCharsRegex)]
          invalidCharPositions.forEach(match => {
            if (match.index !== undefined) {
              errors.push(`Error léxico en línea ${lineIndex + 1}: Carácter no válido '${match[0]}'
En el código:
    ${line}
    ${' '.repeat(match.index)}^ Aquí
Sugerencia: El carácter '${match[0]}' no está permitido en el lenguaje`)
              
              // Agregar a los errores agrupados
              lexicalErrors.push({
                line: lineIndex + 1,
                message: `Carácter no válido '${match[0]}'`,
                code_line: line,
                column: match.index,
                suggestion: `El carácter '${match[0]}' no está permitido en el lenguaje`
              })
            }
          })
        })

        setResult({
          success: false,
          tokens: [],
          errors: errors,
          ast: null,
          output: [],
          phase: 'lexical',
          analysis: {
            lexical: { 
              success: false, 
              tokens: [],
              errors: errors
            },
            syntactic: { success: false, errors: [] },
            semantic: { success: false, errors: [] }
          },
          grouped_errors: {
            lexical: lexicalErrors
          }
        })
      } else {
        const response = await axios.post<CompileResponse>(
          'http://localhost:8000/compile',
          { code }
        )
        
        setResult(response.data)
      }
    } catch (error) {
      console.error('Error al compilar:', error)
      setResult({
        success: false,
        tokens: [],
        errors: ['Error al conectar con el servidor'],
        ast: null,
        output: [],
        phase: 'error'
      })
    }
    setLoading(false)
  }

  return (
    <>
      {showWelcome ? (
        <Welcome onComplete={() => setShowWelcome(false)} />
      ) : (
        <div className="container">
          <h1>Python → TypeScript Compiler</h1>
          
          <div className="split-layout">
            <div className="editor-section">
              <div className="terminal-window">
                <div className="terminal-header">
                  <span className="terminal-title">editor.py</span>
                  <div className="terminal-buttons">
                    <span className="terminal-button minimize"></span>
                    <span className="terminal-button maximize"></span>
                    <span className="terminal-button close"></span>
                  </div>
                </div>
                <div className="editor-terminal-content">
                  <Editor
                    height="100%"
                    defaultLanguage="python"
                    theme="vs-dark"
                    value={code}
                    onChange={(value: string | undefined) => setCode(value || '')}
                    options={{
                      minimap: { enabled: false },
                      fontSize: 14,
                      lineNumbers: 'on',
                      tabSize: 4,
                      insertSpaces: true,
                      detectIndentation: true,
                      trimAutoWhitespace: false,
                      renderWhitespace: "selection",
                      scrollBeyondLastLine: false,
                      padding: { top: 10, bottom: 10 },
                    }}
                  />
                </div>
                <div className="terminal-footer">
                  <button 
                    onClick={handleCompile}
                    disabled={loading}
                    className="compile-button"
                  >
                    {loading ? 'Compilando...' : 'Compilar'}
                  </button>
                </div>
              </div>
            </div>

            <div className="terminal-section">
              <div className="tokens-section">
                <h3>Tabla de Tokens</h3>
                <div className="token-table-container">
                  {result && result.tokens && result.tokens.length > 0 ? (
                    <table className="token-table">
                      <thead>
                        <tr>
                          <th>Tipo</th>
                          <th>Valor</th>
                          <th>Línea</th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.tokens.map((token, index) => (
                          <tr key={index}>
                            <td>{token.type}</td>
                            <td>{token.value || '-'}</td>
                            <td>{token.line}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <div className="output-line">No hay tokens para mostrar</div>
                  )}
                </div>
              </div>

              <Terminal 
                code={code}
                result={result}
                loading={loading}
              />
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default App
