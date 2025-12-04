/**
 * Lazy-loaded components for better performance
 * Reduces initial bundle size and improves First Contentful Paint
 */

'use client'

import dynamic from 'next/dynamic'
import { Loader2 } from 'lucide-react'

/**
 * Loading fallback component
 */
export function ComponentLoader({ message = 'Ładowanie...' }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center p-12">
      <Loader2 className="animate-spin text-purple-500 mb-4" size={48} />
      <p className="text-gray-600 dark:text-gray-400">{message}</p>
    </div>
  )
}

/**
 * Skeleton for chart components
 */
export function ChartSkeleton() {
  return (
    <div className="w-full h-[300px] bg-gray-100 dark:bg-slate-800 rounded-xl animate-pulse flex items-center justify-center">
      <div className="text-gray-400">
        <Loader2 className="animate-spin" size={32} />
      </div>
    </div>
  )
}

/**
 * Skeleton for form components
 */
export function FormSkeleton() {
  return (
    <div className="space-y-4 p-6">
      {[1, 2, 3].map((i) => (
        <div key={i} className="space-y-2">
          <div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-1/4 animate-pulse" />
          <div className="h-10 bg-gray-200 dark:bg-slate-700 rounded animate-pulse" />
        </div>
      ))}
    </div>
  )
}

/**
 * Lazy-loaded Recharts components
 * These are heavy and only needed on specific pages
 */
export const LazyAreaChart = dynamic(
  () => import('recharts').then((mod) => mod.AreaChart),
  {
    loading: () => <ChartSkeleton />,
    ssr: false
  }
)

export const LazyPieChart = dynamic(
  () => import('recharts').then((mod) => mod.PieChart),
  {
    loading: () => <ChartSkeleton />,
    ssr: false
  }
)

export const LazyBarChart = dynamic(
  () => import('recharts').then((mod) => mod.BarChart),
  {
    loading: () => <ChartSkeleton />,
    ssr: false
  }
)

export const LazyLineChart = dynamic(
  () => import('recharts').then((mod) => mod.LineChart),
  {
    loading: () => <ChartSkeleton />,
    ssr: false
  }
)

/**
 * Lazy-loaded page components
 */
export const LazyPlannerPage = dynamic(
  () => import('@/app/planner/page'),
  {
    loading: () => <ComponentLoader message="Ładowanie Plannera..." />,
    ssr: false
  }
)

export const LazyMoodTrackerPage = dynamic(
  () => import('@/app/mood/page'),
  {
    loading: () => <ComponentLoader message="Ładowanie Mood Trackera..." />,
    ssr: false
  }
)

export const LazyDecisionsPage = dynamic(
  () => import('@/app/decisions/page'),
  {
    loading: () => <ComponentLoader message="Ładowanie Decision Helpera..." />,
    ssr: false
  }
)

export const LazyFinancePage = dynamic(
  () => import('@/app/finance/page'),
  {
    loading: () => <ComponentLoader message="Ładowanie Finance Trackera..." />,
    ssr: false
  }
)

export const LazyDashboardPage = dynamic(
  () => import('@/app/dashboard/page'),
  {
    loading: () => <ComponentLoader message="Ładowanie Dashboardu..." />,
    ssr: false
  }
)

export const LazySettingsPage = dynamic(
  () => import('@/app/settings/page'),
  {
    loading: () => <ComponentLoader message="Ładowanie Ustawień..." />,
    ssr: false
  }
)

/**
 * Lazy-loaded UI components
 */
export const LazyNotificationBell = dynamic(
  () => import('@/components/NotificationBell'),
  {
    loading: () => (
      <div className="w-10 h-10 bg-gray-200 dark:bg-slate-700 rounded-full animate-pulse" />
    ),
    ssr: false
  }
)

export const LazySidebar = dynamic(
  () => import('@/components/Sidebar'),
  {
    loading: () => null, // No loading state for sidebar
    ssr: false
  }
)

/**
 * Lazy-loaded modal/dialog components
 */
export const LazyImageViewer = dynamic(
  () => import('@/components/ImageViewer').catch(() => ({
    default: () => <div>Image viewer unavailable</div>
  })),
  {
    loading: () => <ComponentLoader message="Ładowanie podglądu..." />,
    ssr: false
  }
)

/**
 * Conditional lazy loading wrapper
 * Only loads component when condition is met
 */
export function ConditionalLazy({
  condition,
  children,
  fallback = null
}: {
  condition: boolean
  children: React.ReactNode
  fallback?: React.ReactNode
}) {
  if (!condition) {
    return <>{fallback}</>
  }

  return <>{children}</>
}

/**
 * Intersection Observer based lazy loading
 * Component loads when it enters viewport
 */
export function LazyOnView({
  children,
  threshold = 0.1,
  rootMargin = '50px'
}: {
  children: React.ReactNode
  threshold?: number
  rootMargin?: string
}) {
  const [isVisible, setIsVisible] = React.useState(false)
  const ref = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true)
          observer.disconnect()
        }
      },
      { threshold, rootMargin }
    )

    if (ref.current) {
      observer.observe(ref.current)
    }

    return () => observer.disconnect()
  }, [threshold, rootMargin])

  return (
    <div ref={ref}>
      {isVisible ? children : <ComponentLoader />}
    </div>
  )
}

// Re-export React for LazyOnView
import React from 'react'
