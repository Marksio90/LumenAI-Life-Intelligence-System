'use client'

import { useEffect, useState } from 'react'
import { useChatStore } from '@/lib/store'
import { LineChart, Line, AreaChart, Area, PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { TrendingUp, TrendingDown, Minus, MessageSquare, Sparkles, DollarSign, Heart } from 'lucide-react'
import Link from 'next/link'
import DashboardSkeleton from '@/components/DashboardSkeleton'

interface DashboardStats {
  total_conversations: number
  total_messages: number
  active_agents: number
  current_mood: string
  mood_trend: string
  total_expenses: number
  budget_used_percent: number
  messages_this_week: number
}

interface ExpenseChartData {
  timeline: Array<{date: string, amount: number}>
  by_category: Array<{category: string, amount: number, percentage: number, color: string}>
  total: number
}

interface MoodChartData {
  data: Array<{date: string, mood: string, intensity: number, trigger: string}>
  average_intensity: number
  most_common_mood: string
  trend: string
  total_entries: number
}

export default function DashboardPage() {
  const { userId } = useChatStore()
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [expenseData, setExpenseData] = useState<ExpenseChartData | null>(null)
  const [moodData, setMoodData] = useState<MoodChartData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDashboardData()
  }, [userId])

  const fetchDashboardData = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

      // Fetch all dashboard data in parallel
      const [statsRes, expensesRes, moodRes] = await Promise.all([
        fetch(`${apiUrl}/api/v1/dashboard/stats/${userId}`),
        fetch(`${apiUrl}/api/v1/dashboard/expenses-chart/${userId}?days=30`),
        fetch(`${apiUrl}/api/v1/dashboard/mood-chart/${userId}?days=30`)
      ])

      const statsData = await statsRes.json()
      const expensesData = await expensesRes.json()
      const moodChartData = await moodRes.json()

      setStats(statsData.stats)
      setExpenseData(expensesData)
      setMoodData(moodChartData)
    } catch (error) {
      console.error('Error fetching dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <DashboardSkeleton />
  }

  const getTrendIcon = (trend: string) => {
    if (trend === 'improving') return <TrendingUp className="text-green-500" size={20} />
    if (trend === 'declining') return <TrendingDown className="text-red-500" size={20} />
    return <Minus className="text-gray-500" size={20} />
  }

  const getMoodColor = (mood: string) => {
    const colors: Record<string, string> = {
      'happy': '#10b981',
      'sad': '#3b82f6',
      'anxious': '#f59e0b',
      'angry': '#ef4444',
      'neutral': '#6b7280',
      'excited': '#ec4899',
      'calm': '#14b8a6'
    }
    return colors[mood] || '#6b7280'
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 p-6">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold gradient-text mb-2">📊 Dashboard v2.0</h1>
            <p className="text-gray-600 dark:text-gray-400">
              Twoja aktywność i statystyki · Real-time data z MongoDB
            </p>
            <p className="text-xs text-gray-500 mt-1">Ostatnia aktualizacja: {new Date().toLocaleString('pl-PL')}</p>
          </div>
          <Link
            href="/"
            className="px-4 py-2 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-lg hover:from-purple-600 hover:to-blue-600 transition-all shadow-lg"
          >
            💬 Powrót do Chatu
          </Link>
        </div>
      </div>

      <div className="max-w-7xl mx-auto space-y-6">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            icon={<MessageSquare />}
            title="Konwersacje"
            value={stats?.total_conversations || 0}
            color="purple"
          />
          <StatCard
            icon={<Sparkles />}
            title="Wiadomości"
            value={stats?.total_messages || 0}
            color="blue"
          />
          <StatCard
            icon={<Heart />}
            title="Nastrój"
            value={stats?.current_mood || 'neutral'}
            subtitle={getTrendIcon(stats?.mood_trend || 'stable')}
            color="pink"
          />
          <StatCard
            icon={<DollarSign />}
            title="Wydatki"
            value={`${stats?.total_expenses || 0} PLN`}
            color="green"
          />
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Mood Timeline */}
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-gray-200 dark:border-slate-700">
            <h2 className="text-xl font-semibold mb-4 text-gray-800 dark:text-gray-200">
              💭 Timeline Nastroju (30 dni)
            </h2>
            {moodData && moodData.data.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={moodData.data}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 12 }}
                      tickFormatter={(value) => new Date(value).toLocaleDateString('pl-PL', { month: 'short', day: 'numeric' })}
                    />
                    <YAxis domain={[0, 10]} />
                    <Tooltip
                      content={({active, payload}) => {
                        if (active && payload && payload.length) {
                          const data = payload[0].payload
                          return (
                            <div className="bg-white dark:bg-slate-800 p-3 rounded-lg shadow-lg border">
                              <p className="font-semibold">{new Date(data.date).toLocaleDateString('pl-PL')}</p>
                              <p>Nastrój: {data.mood}</p>
                              <p>Intensywność: {data.intensity}/10</p>
                              {data.trigger && <p className="text-sm text-gray-600">Trigger: {data.trigger}</p>}
                            </div>
                          )
                        }
                        return null
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="intensity"
                      stroke="#8b5cf6"
                      fill="#c4b5fd"
                      fillOpacity={0.6}
                    />
                  </AreaChart>
                </ResponsiveContainer>
                <div className="mt-4 flex justify-around text-center">
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Średnia</p>
                    <p className="text-lg font-semibold text-purple-600">{moodData.average_intensity}/10</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Częsty</p>
                    <p className="text-lg font-semibold text-purple-600">{moodData.most_common_mood}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Trend</p>
                    <p className="text-lg font-semibold flex items-center justify-center gap-1">
                      {getTrendIcon(moodData.trend)}
                      <span className="capitalize">{moodData.trend}</span>
                    </p>
                  </div>
                </div>
              </>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-gray-500">
                <p>Zacznij śledzić swój nastrój, aby zobaczyć wykres!</p>
              </div>
            )}
          </div>

          {/* Expense Categories */}
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-gray-200 dark:border-slate-700">
            <h2 className="text-xl font-semibold mb-4 text-gray-800 dark:text-gray-200">
              💰 Wydatki po Kategoriach
            </h2>
            {expenseData && expenseData.total > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={expenseData.by_category.filter(c => c.amount > 0)}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={(entry: any) => `${entry.category}: ${entry.percentage}%`}
                      outerRadius={100}
                      fill="#8884d8"
                      dataKey="amount"
                    >
                      {expenseData.by_category.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
                <div className="mt-4 text-center">
                  <p className="text-sm text-gray-600 dark:text-gray-400">Całkowite wydatki</p>
                  <p className="text-2xl font-bold text-green-600">{expenseData.total} PLN</p>
                </div>
              </>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-gray-500">
                <p>Dodaj wydatki, aby zobaczyć rozkład po kategoriach!</p>
              </div>
            )}
          </div>
        </div>

        {/* Expense Timeline */}
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-gray-200 dark:border-slate-700">
          <h2 className="text-xl font-semibold mb-4 text-gray-800 dark:text-gray-200">
            📈 Wydatki w Czasie (30 dni)
          </h2>
          {expenseData && expenseData.total > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={expenseData.timeline.filter(t => t.amount > 0)}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value) => new Date(value).toLocaleDateString('pl-PL', { month: 'short', day: 'numeric' })}
                />
                <YAxis />
                <Tooltip />
                <Bar dataKey="amount" fill="#10b981" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-gray-500">
              <p>Brak danych o wydatkach. Zacznij dodawać wydatki!</p>
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="bg-gradient-to-r from-purple-500 to-blue-500 rounded-2xl shadow-lg p-6 text-white">
          <h2 className="text-xl font-semibold mb-4">🚀 Szybkie Akcje</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Link
              href="/?action=mood"
              className="bg-white/20 backdrop-blur-sm rounded-lg p-4 hover:bg-white/30 transition-all cursor-pointer"
            >
              <p className="font-semibold mb-1">💭 Zapisz Nastrój</p>
              <p className="text-sm opacity-90">Jak się dzisiaj czujesz?</p>
            </Link>
            <Link
              href="/?action=expense"
              className="bg-white/20 backdrop-blur-sm rounded-lg p-4 hover:bg-white/30 transition-all cursor-pointer"
            >
              <p className="font-semibold mb-1">💰 Dodaj Wydatek</p>
              <p className="text-sm opacity-90">Śledź swoje finanse</p>
            </Link>
            <Link
              href="/"
              className="bg-white/20 backdrop-blur-sm rounded-lg p-4 hover:bg-white/30 transition-all cursor-pointer"
            >
              <p className="font-semibold mb-1">🤖 Porozmawiaj z AI</p>
              <p className="text-sm opacity-90">Wszystkie 7 agentów gotowe</p>
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({ icon, title, value, subtitle, color }: {
  icon: React.ReactNode
  title: string
  value: string | number
  subtitle?: React.ReactNode
  color: string
}) {
  const colorClasses = {
    purple: 'from-purple-500 to-purple-600',
    blue: 'from-blue-500 to-blue-600',
    pink: 'from-pink-500 to-pink-600',
    green: 'from-green-500 to-green-600'
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-gray-200 dark:border-slate-700">
      <div className="flex items-start justify-between mb-3">
        <div className={`p-3 rounded-lg bg-gradient-to-br ${colorClasses[color as keyof typeof colorClasses]} text-white`}>
          {icon}
        </div>
        {subtitle && <div>{subtitle}</div>}
      </div>
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">{title}</p>
      <p className="text-2xl font-bold text-gray-800 dark:text-gray-200">{value}</p>
    </div>
  )
}
