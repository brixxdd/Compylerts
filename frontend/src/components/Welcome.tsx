import { useState, useEffect } from 'react'
import './Welcome.css'

function Welcome({ onComplete }: { onComplete: () => void }) {
  const [showDialog, setShowDialog] = useState(false)
  const [dialogText, setDialogText] = useState('')
  
  useEffect(() => {
    const messages = [
      '¡Hola! Soy TypeSnake 🐍',
      'Te ayudaré a convertir tu código Python a TypeScript',
      '¡Empecemos! 🚀'
    ]
    
    let currentMessage = 0
    setShowDialog(true)
    
    const typeMessage = () => {
      setDialogText(messages[currentMessage])
      currentMessage++
      
      if (currentMessage < messages.length) {
        setTimeout(typeMessage, 2000)
      } else {
        setTimeout(() => {
          setShowDialog(false)
          onComplete()
        }, 2000)
      }
    }
    
    setTimeout(typeMessage, 1000)
  }, [])

  return (
    <div className="welcome-container">
      <div className={`snake-container ${showDialog ? 'show' : 'hide'}`}>
        <img src="/logosnake.png" alt="TypeSnake" className="snake-logo" />
        {showDialog && (
          <div className="dialog-bubble">
            {dialogText}
          </div>
        )}
      </div>
    </div>
  )
}

export default Welcome 