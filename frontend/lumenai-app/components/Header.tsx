'use client'

import { Menu, Sparkles } from 'lucide-react'

interface HeaderProps {
  onMenuClick: () => void
}

export default function Header({ onMenuClick }: HeaderProps) {
  return (
    <header className="bg-white dark:bg-slate-900 border-b border-gray-200 dark:border-slate-800 px-6 py-4">
      <div className="flex items-center justify-between">
        {/* Left: Menu + Logo */}
        <div className="flex items-center gap-4">
          <button
            onClick={onMenuClick}
            className="p-2 hover:bg-gray-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
          >
            <Menu size={24} className="text-gray-700 dark:text-gray-300" />
          </button>

          <div className="flex items-center gap-2">
            <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-blue-500 rounded-xl flex items-center justify-center">
              <Sparkles size={20} className="text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold gradient-text">LumenAI</h1>
              <p className="text-xs text-gray-500 dark:text-gray-400">Life Intelligence System</p>
            </div>
          </div>
        </div>

        {/* Right: Status */}
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          <span className="text-sm text-gray-600 dark:text-gray-400">Online</span>
        </div>
      </div>
    </header>
  )
}
