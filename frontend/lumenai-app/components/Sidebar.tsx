'use client'

import { X, Calendar, Heart, Brain, DollarSign, Settings, Trash2 } from 'lucide-react'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
}

export default function Sidebar({ isOpen, onClose }: SidebarProps) {
  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40 lg:hidden"
        onClick={onClose}
      />

      {/* Sidebar */}
      <aside className="fixed lg:static inset-y-0 left-0 w-80 bg-white dark:bg-slate-900 border-r border-gray-200 dark:border-slate-800 z-50 transform transition-transform lg:transform-none">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-slate-800">
          <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-200">Menu</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-slate-800 rounded-lg transition-colors lg:hidden"
          >
            <X size={20} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-2">
          <NavItem icon={<Calendar />} label="Planner" badge="3" />
          <NavItem icon={<Heart />} label="Mood Tracker" />
          <NavItem icon={<Brain />} label="Decisions" />
          <NavItem icon={<DollarSign />} label="Finance" />
        </nav>

        {/* Divider */}
        <div className="border-t border-gray-200 dark:border-slate-800 my-4" />

        {/* Settings */}
        <div className="p-4 space-y-2">
          <NavItem icon={<Settings />} label="Settings" />
          <NavItem
            icon={<Trash2 />}
            label="Clear Memory"
            variant="danger"
            onClick={() => {
              if (confirm('Czy na pewno chcesz wyczyścić całą pamięć?')) {
                // TODO: Implement clear memory
                alert('Pamięć wyczyszczona!')
              }
            }}
          />
        </div>

        {/* Footer */}
        <div className="absolute bottom-0 left-0 right-0 p-6 border-t border-gray-200 dark:border-slate-800">
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
