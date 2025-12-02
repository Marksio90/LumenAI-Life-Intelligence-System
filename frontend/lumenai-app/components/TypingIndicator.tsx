export default function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="bg-white dark:bg-slate-800 rounded-2xl px-5 py-4 shadow-md border border-gray-200 dark:border-slate-700">
        <div className="flex space-x-2">
          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  )
}
