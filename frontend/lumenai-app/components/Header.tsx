'use client'

import { Menu, Sparkles, BarChart3 } from 'lucide-react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import NotificationBell from './NotificationBell'
import ThemeToggle from './ThemeToggle'

interface HeaderProps {
  onMenuClick: () => void
}

export default function Header({ onMenuClick }: HeaderProps) {
  const pathname = usePathname()

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
            <div className="w-10 h-10 bg-gradient-to-br from-purple-500 via-blue-500 to-cyan-500 rounded-xl flex items-center justify-center shadow-md">
              <Sparkles size={20} className="text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold gradient-text">LumenAI <span className="text-sm text-purple-500">v2.0</span></h1>
              <p className="text-xs text-gray-500 dark:text-gray-400">Life Intelligence · 2025</p>
            </div>
          </div>
        </div>

        {/* Center: Navigation */}
        <nav className="hidden md:flex items-center gap-2">
          <Link
            href="/"
            className={`px-4 py-2 rounded-lg transition-all ${
              pathname === '/'
                ? 'bg-gradient-to-r from-purple-500 to-blue-500 text-white'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-800'
            }`}
          >
            💬 Chat
          </Link>
          <Link
            href="/dashboard"
            className={`px-4 py-2 rounded-lg transition-all flex items-center gap-2 ${
              pathname === '/dashboard'
                ? 'bg-gradient-to-r from-purple-500 to-blue-500 text-white'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-800'
            }`}
          >
            <BarChart3 size={18} />
            Dashboard
          </Link>
        </nav>

        {/* Right: Theme Toggle + Notifications + Status */}
        <div className="flex items-center gap-3">
          <ThemeToggle />
          <NotificationBell />
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span className="text-sm text-gray-600 dark:text-gray-400 hidden sm:inline">Online</span>
          </div>
        </div>
      </div>
    </header>
  )
}
