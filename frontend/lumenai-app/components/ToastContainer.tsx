'use client'

import { useEffect } from 'react'
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from 'lucide-react'
import { useChatStore } from '@/lib/store'

export default function ToastContainer() {
  const { toasts, removeToast } = useChatStore(state => ({
    toasts: state.toasts,
    removeToast: state.removeToast
  }))

  const getIcon = (type: string) => {
    switch (type) {
      case 'success':
        return <CheckCircle size={20} className="text-green-500" />
      case 'error':
        return <AlertCircle size={20} className="text-red-500" />
      case 'warning':
        return <AlertTriangle size={20} className="text-yellow-500" />
      default:
        return <Info size={20} className="text-blue-500" />
    }
  }

  const getStyles = (type: string) => {
    switch (type) {
      case 'success':
        return 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
      case 'error':
        return 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
      case 'warning':
        return 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800'
      default:
        return 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800'
    }
  }

  return (
    <div className="fixed top-20 right-4 z-[100] space-y-2 pointer-events-none">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`
            pointer-events-auto
            min-w-[320px] max-w-md
            flex items-start gap-3
            px-4 py-3 rounded-xl
            border shadow-lg
            backdrop-blur-sm
            animate-in slide-in-from-top-5 fade-in
            ${getStyles(toast.type)}
          `}
        >
          {/* Icon */}
          <div className="flex-shrink-0 mt-0.5">
            {getIcon(toast.type)}
          </div>

          {/* Message */}
          <p className="flex-1 text-sm text-gray-800 dark:text-gray-200 font-medium">
            {toast.message}
          </p>

          {/* Close Button */}
          <button
            onClick={() => removeToast(toast.id)}
            className="flex-shrink-0 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
          >
            <X size={16} />
          </button>
        </div>
      ))}
    </div>
  )
}
