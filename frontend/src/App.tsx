import { useState } from 'react'
import Editor from '@monaco-editor/react'
import axios from 'axios'
import './App.css'

interface CompileResponse {
  success: boolean
  tokens: Array<{
    type: string
    value: string
    line: number
  }>
  errors: string[]
  ast: any
  output: string[]
}

function App() {
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

  const handleCompile = async () => {
    setLoading(true)
    try {
      // Verificar si el código está vacío o solo tiene comentarios/espacios
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
      setResult(response.data)
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
          <h2 className="terminal-title">Terminal</h2>
          {result ? (
            <div className="result-container">
              {result.success ? (
                <div className="output-container">
                  {result.output.map((line, index) => (
                    <div key={index} className="output-line">
                      {line}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="errors-container">
                  <h3>❌ Errores encontrados:</h3>
                  {result.errors.map((error, index) => (
                    <div key={index} className="error">
                      {error}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="output-container">
              <div className="output-line">// El resultado de la compilación aparecerá aquí</div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
