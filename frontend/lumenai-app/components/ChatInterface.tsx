'use client'

import { useState, useEffect, useRef } from 'react'
import { Send, Mic, Image as ImageIcon, Loader2 } from 'lucide-react'
import { useChatStore } from '@/lib/store'
import MessageBubble from './MessageBubble'
import TypingIndicator from './TypingIndicator'

export default function ChatInterface() {
  const [input, setInput] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const { messages, isTyping, sendMessage, connectWebSocket } = useChatStore()

  useEffect(() => {
    // Connect to WebSocket on mount
    connectWebSocket()
  }, [connectWebSocket])

  useEffect(() => {
    // Auto-scroll to bottom when new messages arrive
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  const handleSend = () => {
    if (!input.trim()) return

    sendMessage(input, 'text')
    setInput('')
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleVoiceInput = () => {
    setIsRecording(!isRecording)
    // TODO: Implement voice recording
    alert('Funkcja rozpoznawania mowy będzie wkrótce dostępna!')
  }

  const handleImageUpload = () => {
    // TODO: Implement image upload
    alert('Funkcja przesyłania obrazów będzie wkrótce dostępna!')
  }

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto w-full p-4">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 scroll-smooth">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-20 h-20 mb-6 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">
              <span className="text-4xl">🌟</span>
            </div>
            <h2 className="text-3xl font-bold gradient-text mb-3">
              Witaj w LumenAI!
            </h2>
            <p className="text-gray-600 dark:text-gray-400 max-w-md mb-8">
              Jestem Twoim osobistym asystentem życia. Mogę pomóc Ci w:
            </p>
            <div className="grid grid-cols-2 gap-4 max-w-2xl">
              <FeatureCard icon="📅" title="Planowaniu" desc="Organizacja dnia i zadań" />
              <FeatureCard icon="💭" title="Emocjach" desc="Wsparcie psychiczne" />
              <FeatureCard icon="🤔" title="Decyzjach" desc="Pomoc w wyborach" />
              <FeatureCard icon="💰" title="Finansach" desc="Zarządzanie budżetem" />
            </div>
            <p className="mt-8 text-sm text-gray-500">
              Zacznij rozmowę - powiedz mi, w czym mogę Ci dziś pomóc!
            </p>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {isTyping && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input Area */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-4 border border-gray-200 dark:border-slate-700">
        <div className="flex items-end gap-2">
          {/* Voice Input */}
          <button
            onClick={handleVoiceInput}
            className={`p-3 rounded-xl transition-all ${
              isRecording
                ? 'bg-red-500 text-white animate-pulse'
                : 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-600'
            }`}
            title="Nagrywanie głosowe"
          >
            <Mic size={20} />
          </button>

          {/* Image Upload */}
          <button
            onClick={handleImageUpload}
            className="p-3 rounded-xl bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-600 transition-all"
            title="Prześlij obraz"
          >
            <ImageIcon size={20} />
          </button>

          {/* Text Input */}
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Napisz wiadomość..."
            className="flex-1 resize-none bg-transparent border-none outline-none px-4 py-3 text-gray-800 dark:text-gray-200 placeholder-gray-400 max-h-32"
            rows={1}
            style={{
              minHeight: '44px',
              maxHeight: '128px'
            }}
          />

          {/* Send Button */}
          <button
            onClick={handleSend}
            disabled={!input.trim()}
            className="p-3 rounded-xl bg-gradient-to-r from-purple-500 to-blue-500 text-white hover:from-purple-600 hover:to-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            <Send size={20} />
          </button>
        </div>
      </div>
    </div>
  )
}

function FeatureCard({ icon, title, desc }: { icon: string, title: string, desc: string }) {
  return (
    <div className="p-4 bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 hover:shadow-md transition-shadow">
      <div className="text-2xl mb-2">{icon}</div>
      <h3 className="font-semibold text-gray-800 dark:text-gray-200">{title}</h3>
      <p className="text-xs text-gray-500 dark:text-gray-400">{desc}</p>
    </div>
  )
}
