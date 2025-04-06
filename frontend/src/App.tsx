import { useState } from 'react'
import Editor from '@monaco-editor/react'
import axios from 'axios'
import './App.css'
import Welcome from './components/Welcome'

interface Token {
  type: string
  value: string
  line: number
}

interface CompileResponse {
  success: boolean
  tokens: Token[]
  errors: string[]
  ast: any
  output: string[]
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
          output: []
        })
        setLoading(false)
        return
      }

      const response = await axios.post<CompileResponse>(
        'http://localhost:8000/compile',
        { code }
      )
      
      // Extraer tokens del output
      const tokens = parseTokensFromOutput(response.data.output)
      
      setResult({
        ...response.data,
        tokens: tokens
      })
    } catch (error) {
      console.error('Error al compilar:', error)
      setResult({
        success: false,
        tokens: [],
        errors: ['Error al conectar con el servidor'],
        ast: null,
        output: []
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
              <div className="editor-container">
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
                  }}
                />
              </div>
              <button 
                onClick={handleCompile}
                disabled={loading}
                className="compile-button"
              >
                {loading ? 'Compilando...' : 'Compilar'}
              </button>
            </div>

            <div className="terminal-section">
              <div className="terminal-content">
                <div className="tokens-section">
                  <h3>Tabla de Tokens</h3>
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

                <div className="console-section">
                  <h3>Consola</h3>
                  {result ? (
                    result.success ? (
                      <div className="success-message">
                        <div>✅ Compilación exitosa</div>
                        {result.output && result.output.filter(line => 
                          !line.includes(':') || 
                          line.includes('----------------------------------------') ||
                          line.includes('encontraron errores') ||
                          line.includes('Análisis completado')
                        ).map((line, index) => (
                          <div key={index} className="output-line">{line}</div>
                        ))}
                      </div>
                    ) : (
                      <div className="errors-container">
                        {result.errors && result.errors.map((error, index) => (
                          <div key={index} className="error-message">{error}</div>
                        ))}
                      </div>
                    )
                  ) : (
                    <div className="output-line">
                      // El resultado de la compilación aparecerá aquí
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default App
