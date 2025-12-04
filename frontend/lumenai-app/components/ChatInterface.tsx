'use client'

import { useState, useEffect, useRef } from 'react'
import { Send, Mic, Image as ImageIcon, Loader2, X } from 'lucide-react'
import { useChatStore } from '@/lib/store'
import MessageBubble from './MessageBubble'
import TypingIndicator from './TypingIndicator'
import { compressImage, getCompressionStats, formatBytes } from '@/lib/imageCompression'
import { createOptimizedRecorder, formatAudioSize, createAudioFileName } from '@/lib/audioCompression'

export default function ChatInterface() {
  const [input, setInput] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [selectedImage, setSelectedImage] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null)
  const [audioChunks, setAudioChunks] = useState<Blob[]>([])

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { messages, isTyping, sendMessage, connectWebSocket, userId, addMessage, addToast } = useChatStore(state => ({
    messages: state.messages,
    isTyping: state.isTyping,
    sendMessage: state.sendMessage,
    connectWebSocket: state.connectWebSocket,
    userId: state.userId,
    addMessage: state.addMessage,
    addToast: state.addToast
  }))

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

  const handleVoiceInput = async () => {
    if (!isRecording) {
      // Start recording
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true
          }
        })

        // Create optimized recorder with better codec
        const recorder = await createOptimizedRecorder(stream, {
          audioBitsPerSecond: 64000 // 64kbps - good quality, small size
        })

        const chunks: Blob[] = []

        recorder.ondataavailable = (e) => {
          if (e.data.size > 0) {
            chunks.push(e.data)
          }
        }

        recorder.onstop = async () => {
          const audioBlob = new Blob(chunks, { type: recorder.mimeType })

          // Show audio stats
          addToast({
            message: `🎤 Nagranie: ${formatAudioSize(audioBlob.size)}`,
            type: 'success'
          })

          await uploadAudio(audioBlob)

          // Stop all tracks
          stream.getTracks().forEach(track => track.stop())
        }

        recorder.start()
        setMediaRecorder(recorder)
        setIsRecording(true)
        setAudioChunks(chunks)

        addToast({
          message: '🎙️ Nagrywanie rozpoczęte - kliknij ponownie aby zakończyć',
          type: 'success'
        })
      } catch (err) {
        console.error('Error accessing microphone:', err)
        addToast({
          message: 'Nie mogę uzyskać dostępu do mikrofonu. Sprawdź uprawnienia przeglądarki.',
          type: 'error'
        })
      }
    } else {
      // Stop recording
      if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop()
        setIsRecording(false)
      }
    }
  }

  const uploadAudio = async (audioBlob: Blob) => {
    setIsUploading(true)

    try {
      const formData = new FormData()
      const fileName = createAudioFileName('voice_message')
      formData.append('file', audioBlob, fileName)
      formData.append('user_id', userId)
      formData.append('message', input || 'Transkrybuj to nagranie')
      formData.append('language', 'pl')

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/v1/upload/audio`, {
        method: 'POST',
        body: formData
      })

      const data = await response.json()

      if (data.status === 'success') {
        // Add user message
        addMessage({
          id: `msg_${Date.now()}`,
          role: 'user',
          content: input || '🎤 Nagranie audio',
          timestamp: new Date()
        })

        // Add assistant response
        addMessage({
          id: `msg_${Date.now() + 1}`,
          role: 'assistant',
          content: data.response,
          timestamp: new Date(),
          agent: data.agent
        })

        setInput('')
      } else {
        addToast({
          message: 'Błąd podczas przetwarzania audio',
          type: 'error'
        })
      }
    } catch (err) {
      console.error('Error uploading audio:', err)
      addToast({
        message: 'Wystąpił błąd podczas przesyłania nagrania',
        type: 'error'
      })
    } finally {
      setIsUploading(false)
    }
  }

  const handleImageUpload = () => {
    fileInputRef.current?.click()
  }

  const handleImageSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file && file.type.startsWith('image/')) {
      try {
        setIsUploading(true)

        // Compress image
        const compressedFile = await compressImage(file, {
          maxSizeMB: 1,
          maxWidthOrHeight: 1920,
          quality: 0.8
        })

        // Show compression stats
        const stats = getCompressionStats(file, compressedFile)
        if (stats.savedPercentage > 10) {
          addToast({
            message: `📦 Obraz skompresowany: ${stats.originalSize} → ${stats.compressedSize} (oszczędzono ${stats.savedPercentage}%)`,
            type: 'success'
          })
        }

        setSelectedImage(compressedFile)

        // Create preview
        const reader = new FileReader()
        reader.onloadend = () => {
          setImagePreview(reader.result as string)
        }
        reader.readAsDataURL(compressedFile)
      } catch (error) {
        console.error('Error compressing image:', error)
        addToast({
          message: 'Błąd podczas kompresji obrazu. Używam oryginalnego pliku.',
          type: 'error'
        })
        // Fallback to original file
        setSelectedImage(file)
        const reader = new FileReader()
        reader.onloadend = () => {
          setImagePreview(reader.result as string)
        }
        reader.readAsDataURL(file)
      } finally {
        setIsUploading(false)
      }
    }
  }

  const handleSendImage = async () => {
    if (!selectedImage) return

    setIsUploading(true)

    try {
      const formData = new FormData()
      formData.append('file', selectedImage)
      formData.append('user_id', userId)
      formData.append('message', input || 'Co jest na tym zdjęciu?')

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/v1/upload/image`, {
        method: 'POST',
        body: formData
      })

      const data = await response.json()

      if (data.status === 'success') {
        // Add user message with image indicator
        addMessage({
          id: `msg_${Date.now()}`,
          role: 'user',
          content: `📷 ${input || 'Przesłano obraz'}`,
          timestamp: new Date()
        })

        // Add assistant response
        addMessage({
          id: `msg_${Date.now() + 1}`,
          role: 'assistant',
          content: data.response,
          timestamp: new Date(),
          agent: data.agent
        })

        // Clear input and image
        setInput('')
        setSelectedImage(null)
        setImagePreview(null)
      } else {
        addToast({
          message: 'Błąd podczas przetwarzania obrazu',
          type: 'error'
        })
      }
    } catch (err) {
      console.error('Error uploading image:', err)
      addToast({
        message: 'Wystąpił błąd podczas przesyłania obrazu',
        type: 'error'
      })
    } finally {
      setIsUploading(false)
    }
  }

  const cancelImageUpload = () => {
    setSelectedImage(null)
    setImagePreview(null)
  }

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto w-full p-4">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 scroll-smooth">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-24 h-24 mb-6 rounded-full bg-gradient-to-br from-purple-500 via-blue-500 to-cyan-500 flex items-center justify-center shadow-lg animate-pulse">
              <span className="text-5xl">🌟</span>
            </div>
            <h2 className="text-4xl font-bold gradient-text mb-2">
              Witaj w LumenAI v2.0
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-500 mb-4">
              © 2025 · Twój Osobisty AI Companion
            </p>
            <p className="text-gray-600 dark:text-gray-400 max-w-lg mb-8 text-lg">
              Jestem Twoim wielomodalnym asystentem życia, gotowy wspierać Cię w codziennych wyzwaniach:
            </p>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 max-w-4xl">
              <FeatureCard icon="📅" title="Planowanie" desc="Zadania · Kalendarz · Google Calendar" />
              <FeatureCard icon="💭" title="Wsparcie Emocjonalne" desc="CBT/DBT · Mood tracking" />
              <FeatureCard icon="🤔" title="Decyzje" desc="Analiza scenariuszy · Pros/Cons" />
              <FeatureCard icon="💰" title="Finanse" desc="Budżet · Wydatki · Cele" />
              <FeatureCard icon="🔍" title="Wizja AI" desc="OCR · Dokumenty · Twarze" />
              <FeatureCard icon="🎤" title="Głos & Audio" desc="STT · Transkrypcja" />
              <FeatureCard icon="🤖" title="Automatyzacja" desc="Gmail · Notion · Kalendarz" />
              <FeatureCard icon="📊" title="Analityka" desc="Trendy · Wzorce · Insights" />
            </div>
            <p className="mt-8 text-base font-medium text-gray-700 dark:text-gray-300">
              💬 Jak mogę Ci dzisiaj pomóc?
            </p>
            <p className="mt-2 text-xs text-gray-500">
              Napisz wiadomość, nagraj głos lub prześlij obraz →
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
        {/* Image Preview */}
        {imagePreview && (
          <div className="mb-3 relative">
            <div className="relative inline-block">
              <img
                src={imagePreview}
                alt="Preview"
                className="max-h-32 rounded-lg border border-gray-300 dark:border-gray-600"
              />
              <button
                onClick={cancelImageUpload}
                className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 hover:bg-red-600"
              >
                <X size={16} />
              </button>
            </div>
          </div>
        )}

        {/* Recording Indicator */}
        {isRecording && (
          <div className="mb-3 flex items-center gap-2 text-red-500">
            <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
            <span className="text-sm font-medium">Nagrywanie...</span>
          </div>
        )}

        {/* Uploading Indicator */}
        {isUploading && (
          <div className="mb-3 flex items-center gap-2 text-purple-500">
            <Loader2 className="animate-spin" size={16} />
            <span className="text-sm font-medium">Przesyłanie...</span>
          </div>
        )}

        <div className="flex items-end gap-2">
          {/* Voice Input */}
          <button
            onClick={handleVoiceInput}
            disabled={isUploading}
            className={`p-3 rounded-xl transition-all ${
              isRecording
                ? 'bg-red-500 text-white animate-pulse'
                : 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-600 disabled:opacity-50'
            }`}
            title={isRecording ? 'Zatrzymaj nagrywanie' : 'Nagrywanie głosowe'}
          >
            <Mic size={20} />
          </button>

          {/* Image Upload */}
          <button
            onClick={handleImageUpload}
            disabled={isUploading || isRecording}
            className="p-3 rounded-xl bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-600 transition-all disabled:opacity-50"
            title="Prześlij obraz"
          >
            <ImageIcon size={20} />
          </button>

          {/* Hidden File Input */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleImageSelect}
            className="hidden"
          />

          {/* Text Input */}
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Napisz wiadomość..."
            disabled={isUploading}
            className="flex-1 resize-none bg-transparent border-none outline-none px-4 py-3 text-gray-800 dark:text-gray-200 placeholder-gray-400 max-h-32 disabled:opacity-50"
            rows={1}
            style={{
              minHeight: '44px',
              maxHeight: '128px'
            }}
          />

          {/* Send Button */}
          <button
            onClick={selectedImage ? handleSendImage : handleSend}
            disabled={(!input.trim() && !selectedImage) || isUploading}
            className="p-3 rounded-xl bg-gradient-to-r from-purple-500 to-blue-500 text-white hover:from-purple-600 hover:to-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {isUploading ? <Loader2 className="animate-spin" size={20} /> : <Send size={20} />}
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
