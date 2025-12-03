export default function DashboardSkeleton() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-950 p-6 animate-pulse">
      <div className="max-w-7xl mx-auto">
        {/* Header Skeleton */}
        <div className="mb-8">
          <div className="h-10 w-64 bg-gray-200 dark:bg-slate-800 rounded-lg mb-2"></div>
          <div className="h-5 w-96 bg-gray-200 dark:bg-slate-800 rounded-lg"></div>
        </div>

        {/* Stats Cards Skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-white dark:bg-slate-900 rounded-2xl p-6 border border-gray-200 dark:border-slate-800">
              <div className="flex items-center justify-between mb-4">
                <div className="w-12 h-12 bg-gray-200 dark:bg-slate-800 rounded-xl"></div>
                <div className="w-20 h-6 bg-gray-200 dark:bg-slate-800 rounded-lg"></div>
              </div>
              <div className="h-8 w-24 bg-gray-200 dark:bg-slate-800 rounded-lg mb-2"></div>
              <div className="h-4 w-32 bg-gray-200 dark:bg-slate-800 rounded-lg"></div>
            </div>
          ))}
        </div>

        {/* Charts Grid Skeleton */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Mood Chart Skeleton */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 border border-gray-200 dark:border-slate-800">
            <div className="flex items-center justify-between mb-6">
              <div className="h-6 w-48 bg-gray-200 dark:bg-slate-800 rounded-lg"></div>
              <div className="w-20 h-5 bg-gray-200 dark:bg-slate-800 rounded-lg"></div>
            </div>
            <div className="h-64 bg-gray-100 dark:bg-slate-800/50 rounded-lg"></div>
          </div>

          {/* Expense Pie Chart Skeleton */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 border border-gray-200 dark:border-slate-800">
            <div className="flex items-center justify-between mb-6">
              <div className="h-6 w-48 bg-gray-200 dark:bg-slate-800 rounded-lg"></div>
              <div className="w-20 h-5 bg-gray-200 dark:bg-slate-800 rounded-lg"></div>
            </div>
            <div className="flex items-center justify-center">
              <div className="w-48 h-48 bg-gray-100 dark:bg-slate-800/50 rounded-full"></div>
            </div>
          </div>
        </div>

        {/* Expense Timeline Skeleton */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 border border-gray-200 dark:border-slate-800 mb-8">
          <div className="flex items-center justify-between mb-6">
            <div className="h-6 w-56 bg-gray-200 dark:bg-slate-800 rounded-lg"></div>
            <div className="w-24 h-5 bg-gray-200 dark:bg-slate-800 rounded-lg"></div>
          </div>
          <div className="h-80 bg-gray-100 dark:bg-slate-800/50 rounded-lg"></div>
        </div>

        {/* Quick Actions Skeleton */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 border border-gray-200 dark:border-slate-800">
          <div className="h-6 w-48 bg-gray-200 dark:bg-slate-800 rounded-lg mb-6"></div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-24 bg-gray-100 dark:bg-slate-800/50 rounded-xl"></div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
