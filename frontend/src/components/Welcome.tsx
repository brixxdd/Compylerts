import { useState, useEffect, useRef } from 'react'
import './Welcome.css'

function Welcome({ onComplete }: { onComplete: () => void }) {
  const [showDialog, setShowDialog] = useState(false)
  const [dialogText, setDialogText] = useState('')
  const [isReady, setIsReady] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  
  const startPresentation = () => {
    setIsReady(true)
    const messages = [
      { text: '¡Hola! Soy TypeSnake 🐍', audio: '/songs/1.-bienvenida.mp3', duration: 2000 },
      { text: 'Te ayudaré a convertir tu código Python a TypeScript', audio: '', duration: 3500 },
      { text: '¡Empecemos! 🚀', audio: '', duration: 1000 }
    ]
    
    let currentMessage = 0
    setShowDialog(true)
    
    const playAudio = async (audioSrc: string) => {
      try {
        if (audioRef.current) {
          audioRef.current.src = audioSrc
          audioRef.current.load()
          await audioRef.current.play()
        }
      } catch (error) {
        console.error('Error reproduciendo audio:', error)
      }
    }
    
    const typeMessage = async () => {
      const message = messages[currentMessage]
      setDialogText(message.text)
      
      if (message.audio) {
        await playAudio(message.audio)
      }
      
      currentMessage++
      
      if (currentMessage < messages.length) {
        setTimeout(typeMessage, message.duration)
      } else {
        setTimeout(() => {
          setShowDialog(false)
          onComplete()
        }, message.duration)
      }
    }
    
    typeMessage()
  }

  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current.src = ''
      }
    }
  }, [])

  return (
    <div className="welcome-container">
      <audio 
        ref={audioRef}
        preload="auto"
      />
      {!isReady ? (
        <div className="start-container">
          <img src="/logosnake.png" alt="TypeSnake" className="snake-logo" />
          <button 
            className="start-button"
            onClick={startPresentation}
          >
            Comenzar 🎯
          </button>
        </div>
      ) : (
        <div className={`snake-container ${showDialog ? 'show' : 'hide'}`}>
          <img src="/logosnake.png" alt="TypeSnake" className="snake-logo" />
          {showDialog && (
            <div className="dialog-bubble">
              {dialogText}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default Welcome 