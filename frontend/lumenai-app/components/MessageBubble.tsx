'use client'

import ReactMarkdown from 'react-markdown'
import { format } from 'date-fns'
import { pl } from 'date-fns/locale'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  agent?: string
}

export default function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} message-enter`}>
      <div className={`max-w-[80%] ${isUser ? 'order-2' : 'order-1'}`}>
        {/* Agent Label */}
        {!isUser && message.agent && (
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1 ml-3">
            {getAgentEmoji(message.agent)} {getAgentName(message.agent)}
          </div>
        )}

        {/* Message Content */}
        <div
          className={`rounded-2xl px-5 py-3 ${
            isUser
              ? 'bg-gradient-to-r from-purple-500 to-blue-500 text-white'
              : 'bg-white dark:bg-slate-800 text-gray-800 dark:text-gray-200 shadow-md border border-gray-200 dark:border-slate-700'
          }`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Timestamp */}
        <div className={`text-xs text-gray-400 mt-1 ${isUser ? 'text-right mr-3' : 'ml-3'}`}>
          {format(message.timestamp, 'HH:mm', { locale: pl })}
        </div>
      </div>
    </div>
  )
}

function getAgentEmoji(agent: string): string {
  const emojis: Record<string, string> = {
    planner: '📅',
    mood: '💭',
    decision: '🤔',
    finance: '💰',
    vision: '👁️',
    speech: '🎤',
    general: '🌟'
  }
  return emojis[agent] || '🤖'
}

function getAgentName(agent: string): string {
  const names: Record<string, string> = {
    planner: 'Planista',
    mood: 'Wsparcie Emocjonalne',
    decision: 'Doradca',
    finance: 'Finanse',
    vision: 'Analiza Obrazu',
    speech: 'Rozpoznawanie Mowy',
    general: 'LumenAI'
  }
  return names[agent] || 'LumenAI'
}
