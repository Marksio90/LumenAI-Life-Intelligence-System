import { create } from 'zustand'
import { io, Socket } from 'socket.io-client'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  agent?: string
}

interface ChatState {
  messages: Message[]
  isTyping: boolean
  isConnected: boolean
  socket: Socket | null
  userId: string
  addMessage: (message: Message) => void
  sendMessage: (content: string, type: string) => void
  setTyping: (typing: boolean) => void
  connectWebSocket: () => void
  disconnectWebSocket: () => void
  clearMessages: () => void
}

const generateUserId = () => {
  // Generate or retrieve user ID from localStorage
  if (typeof window !== 'undefined') {
    let userId = localStorage.getItem('lumenai_user_id')
    if (!userId) {
      userId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      localStorage.setItem('lumenai_user_id', userId)
    }
    return userId
  }
  return 'anonymous'
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isTyping: false,
  isConnected: false,
  socket: null,
  userId: generateUserId(),

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message]
    })),

  setTyping: (typing) =>
    set({ isTyping: typing }),

  sendMessage: (content, type = 'text') => {
    const { socket, userId, addMessage } = get()

    // Add user message to chat
    const userMessage: Message = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date()
    }
    addMessage(userMessage)

    // Send via WebSocket if connected
    if (socket && socket.connected) {
      socket.emit('message', {
        user_id: userId,
        message: content,
        type,
        metadata: {}
      })

      set({ isTyping: true })
    } else {
      // Fallback to REST API
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

      fetch(`${apiUrl}/api/v1/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          message: content,
          type
        })
      })
        .then((res) => res.json())
        .then((data) => {
          const assistantMessage: Message = {
            id: `msg_${Date.now()}`,
            role: 'assistant',
            content: data.content || 'Przepraszam, wystąpił błąd.',
            timestamp: new Date(),
            agent: data.agent
          }
          addMessage(assistantMessage)
        })
        .catch((err) => {
          console.error('Error sending message:', err)
          const errorMessage: Message = {
            id: `msg_${Date.now()}`,
            role: 'assistant',
            content: 'Przepraszam, nie mogę połączyć się z serwerem. Upewnij się, że backend jest uruchomiony.',
            timestamp: new Date(),
            agent: 'error'
          }
          addMessage(errorMessage)
        })
        .finally(() => {
          set({ isTyping: false })
        })
    }
  },

  connectWebSocket: () => {
    const { userId } = get()
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'

    try {
      const socket = io(wsUrl, {
        transports: ['websocket'],
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000
      })

      socket.on('connect', () => {
        console.log('✅ WebSocket connected')
        set({ isConnected: true })
      })

      socket.on('disconnect', () => {
        console.log('❌ WebSocket disconnected')
        set({ isConnected: false })
      })

      socket.on('message', (data) => {
        const { addMessage, setTyping } = get()

        setTyping(false)

        if (data.type === 'message') {
          const assistantMessage: Message = {
            id: `msg_${Date.now()}`,
            role: 'assistant',
            content: data.content,
            timestamp: new Date(),
            agent: data.agent
          }
          addMessage(assistantMessage)
        }
      })

      socket.on('status', (data) => {
        if (data.status === 'typing') {
          set({ isTyping: true })
        }
      })

      socket.on('error', (error) => {
        console.error('WebSocket error:', error)
      })

      set({ socket })
    } catch (error) {
      console.error('Failed to connect WebSocket:', error)
      set({ isConnected: false })
    }
  },

  disconnectWebSocket: () => {
    const { socket } = get()
    if (socket) {
      socket.disconnect()
      set({ socket: null, isConnected: false })
    }
  },

  clearMessages: () => {
    set({ messages: [] })
  }
}))
