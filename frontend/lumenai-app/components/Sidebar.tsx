'use client'

import { useState, useEffect } from 'react'
import { X, Calendar, Heart, Brain, DollarSign, Settings, Trash2, MessageSquare, Plus, Loader2 } from 'lucide-react'
import { useChatStore } from '@/lib/store'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
}

interface Conversation {
  conversation_id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

export default function Sidebar({ isOpen, onClose }: SidebarProps) {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null)

  const { userId, clearMessages, addMessage } = useChatStore(state => ({
    userId: state.userId,
    clearMessages: state.clearMessages,
    addMessage: state.addMessage
  }))

  useEffect(() => {
    if (isOpen) {
      fetchConversations()
    }
  }, [isOpen, userId])

  const fetchConversations = async () => {
    setIsLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/v1/user/${userId}/conversations?limit=50`)
      const data = await response.json()

      if (data.status === 'success') {
        setConversations(data.conversations)
      }
    } catch (err) {
      console.error('Error fetching conversations:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const loadConversation = async (conversationId: string) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/v1/conversation/${conversationId}/messages?limit=100`)
      const data = await response.json()

      if (data.status === 'success') {
        clearMessages()

        // Load messages into chat
        data.messages.forEach((msg: any) => {
          addMessage({
            id: msg.message_id,
            role: msg.role,
            content: msg.content,
            timestamp: new Date(msg.timestamp),
            agent: msg.metadata?.agent
          })
        })

        setActiveConversationId(conversationId)
        onClose() // Close sidebar on mobile after loading
      }
    } catch (err) {
      console.error('Error loading conversation:', err)
      alert('Nie udało się załadować konwersacji')
    }
  }

  const startNewChat = () => {
    clearMessages()
    setActiveConversationId(null)
    onClose()
  }

  const handleClearMemory = async () => {
    if (!confirm('Czy na pewno chcesz wyczyścić całą pamięć? Ta akcja jest nieodwracalna.')) {
      return
    }

    try {
      clearMessages()
      setConversations([])
      setActiveConversationId(null)
      alert('Pamięć lokalna wyczyszczona! (Historia pozostała w bazie danych)')
    } catch (err) {
      console.error('Error clearing memory:', err)
      alert('Wystąpił błąd podczas czyszczenia pamięci')
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const days = Math.floor(diff / 86400000)

    if (days === 0) return 'Dziś'
    if (days === 1) return 'Wczoraj'
    if (days < 7) return `${days} dni temu`
    return date.toLocaleDateString('pl-PL', { month: 'short', day: 'numeric' })
  }

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40 lg:hidden"
        onClick={onClose}
      />

      {/* Sidebar */}
      <aside className="fixed lg:static inset-y-0 left-0 w-80 bg-white dark:bg-slate-900 border-r border-gray-200 dark:border-slate-800 z-50 transform transition-transform lg:transform-none flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-slate-800">
          <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-200">LumenAI</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-slate-800 rounded-lg transition-colors lg:hidden"
          >
            <X size={20} />
          </button>
        </div>

        {/* New Chat Button */}
        <div className="p-4">
          <button
            onClick={startNewChat}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-xl hover:from-purple-600 hover:to-blue-600 transition-all font-medium"
          >
            <Plus size={20} />
            <span>Nowa rozmowa</span>
          </button>
        </div>

        {/* Conversations List */}
        <div className="flex-1 overflow-y-auto px-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
              Historia
            </h3>
            {conversations.length > 0 && (
              <span className="text-xs text-gray-400">
                {conversations.length}
              </span>
            )}
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-8 text-gray-500">
              <Loader2 className="animate-spin" size={24} />
            </div>
          ) : conversations.length === 0 ? (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <MessageSquare size={48} className="mx-auto mb-3 opacity-30" />
              <p className="text-sm">Brak historii</p>
              <p className="text-xs mt-1">Rozpocznij nową rozmowę</p>
            </div>
          ) : (
            <div className="space-y-2 pb-4">
              {conversations.map((conv) => (
                <button
                  key={conv.conversation_id}
                  onClick={() => loadConversation(conv.conversation_id)}
                  className={`w-full text-left px-4 py-3 rounded-xl transition-all ${
                    activeConversationId === conv.conversation_id
                      ? 'bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800'
                      : 'hover:bg-gray-100 dark:hover:bg-slate-800 border border-transparent'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <MessageSquare
                      size={18}
                      className={`flex-shrink-0 mt-0.5 ${
                        activeConversationId === conv.conversation_id
                          ? 'text-purple-500'
                          : 'text-gray-400 dark:text-gray-500'
                      }`}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm text-gray-800 dark:text-gray-200 truncate">
                        {conv.title || 'Bez tytułu'}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {formatDate(conv.updated_at)}
                        </span>
                        <span className="text-xs text-gray-400">•</span>
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {conv.message_count} wiad.
                        </span>
                      </div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Divider */}
        <div className="border-t border-gray-200 dark:border-slate-800" />

        {/* Quick Actions */}
        <nav className="p-4 space-y-2">
          <NavItem icon={<Calendar />} label="Planner" />
          <NavItem icon={<Heart />} label="Mood Tracker" />
          <NavItem icon={<Brain />} label="Decisions" />
          <NavItem icon={<DollarSign />} label="Finance" />
        </nav>

        {/* Divider */}
        <div className="border-t border-gray-200 dark:border-slate-800" />

        {/* Settings */}
        <div className="p-4 space-y-2">
          <NavItem icon={<Settings />} label="Settings" />
          <NavItem
            icon={<Trash2 />}
            label="Clear Memory"
            variant="danger"
            onClick={handleClearMemory}
          />
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200 dark:border-slate-800">
          <div className="text-xs text-gray-500 dark:text-gray-400 text-center">
            <p>LumenAI v1.0.0</p>
            <p className="mt-1">© 2024 Life Intelligence</p>
          </div>
        </div>
      </aside>
    </>
  )
}

interface NavItemProps {
  icon: React.ReactNode
  label: string
  badge?: string
  variant?: 'default' | 'danger'
  onClick?: () => void
}

function NavItem({ icon, label, badge, variant = 'default', onClick }: NavItemProps) {
  const baseClasses = "flex items-center justify-between w-full px-4 py-3 rounded-xl transition-colors"
  const variantClasses = variant === 'danger'
    ? "text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20"
    : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-800"

  return (
    <button className={`${baseClasses} ${variantClasses}`} onClick={onClick}>
      <div className="flex items-center gap-3">
        <div className="w-5 h-5">{icon}</div>
        <span className="font-medium">{label}</span>
      </div>
      {badge && (
        <span className="px-2 py-1 text-xs bg-purple-500 text-white rounded-full">
          {badge}
        </span>
      )}
    </button>
  )
}
