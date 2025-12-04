'use client'

import { useEffect, useState } from 'react'
import { useChatStore } from '@/lib/store'
import { Heart, TrendingUp, TrendingDown, Minus, Plus, Calendar, Sparkles, Loader2 } from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import Link from 'next/link'

interface MoodEntry {
  mood_id: string
  mood: string
  intensity: number
  trigger?: string
  notes?: string
  timestamp: string
}

interface MoodStats {
  total_entries: number
  average_intensity: number
  most_common_mood: string
  trend: 'improving' | 'declining' | 'stable'
  mood_distribution: Array<{ mood: string; count: number; percentage: number }>
}

const MOOD_OPTIONS = [
  { value: 'happy', label: '😊 Szczęśliwy', color: '#10b981' },
  { value: 'sad', label: '😢 Smutny', color: '#3b82f6' },
  { value: 'anxious', label: '😰 Zaniepokojony', color: '#f59e0b' },
  { value: 'angry', label: '😠 Zły', color: '#ef4444' },
  { value: 'neutral', label: '😐 Neutralny', color: '#6b7280' },
  { value: 'excited', label: '🤩 Podekscytowany', color: '#ec4899' },
  { value: 'calm', label: '😌 Spokojny', color: '#14b8a6' },
  { value: 'stressed', label: '😫 Zestresowany', color: '#f97316' },
  { value: 'confused', label: '😕 Zdezorientowany', color: '#8b5cf6' },
  { value: 'grateful', label: '🙏 Wdzięczny', color: '#06b6d4' }
]

export default function MoodTrackerPage() {
  const { userId, addToast } = useChatStore()
  const [entries, setEntries] = useState<MoodEntry[]>([])
  const [stats, setStats] = useState<MoodStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [showAddMood, setShowAddMood] = useState(false)

  // New mood entry state
  const [selectedMood, setSelectedMood] = useState<string>('')
  const [intensity, setIntensity] = useState<number>(5)
  const [trigger, setTrigger] = useState<string>('')
  const [notes, setNotes] = useState<string>('')

  useEffect(() => {
    fetchMoodData()
  }, [userId])

  const fetchMoodData = async () => {
    setLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

      // Fetch mood entries
      const entriesRes = await fetch(`${apiUrl}/api/v1/mood/${userId}/entries?limit=30`)
      const entriesData = await entriesRes.json()

      if (entriesData.status === 'success') {
        setEntries(entriesData.entries || [])
      }

      // Fetch mood stats
      const statsRes = await fetch(`${apiUrl}/api/v1/mood/${userId}/stats`)
      const statsData = await statsRes.json()

      if (statsData.status === 'success') {
        setStats(statsData.stats)
      }
    } catch (error) {
      console.error('Error fetching mood data:', error)
      addToast({
        message: 'Nie udało się załadować danych nastroju',
        type: 'error'
      })
    } finally {
      setLoading(false)
    }
  }

  const addMoodEntry = async () => {
    if (!selectedMood) {
      addToast({
        message: 'Wybierz nastrój',
        type: 'error'
      })
      return
    }

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/v1/mood/${userId}/entries`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mood: selectedMood,
          intensity,
          trigger: trigger || null,
          notes: notes || null
        })
      })

      const data = await response.json()

      if (data.status === 'success') {
        addToast({
          message: '✅ Nastrój zapisany!',
          type: 'success'
        })
        setShowAddMood(false)
        resetMoodForm()
        await fetchMoodData()
      }
    } catch (error) {
      console.error('Error adding mood entry:', error)
      addToast({
        message: 'Nie udało się zapisać nastroju',
        type: 'error'
      })
    }
  }

  const resetMoodForm = () => {
    setSelectedMood('')
    setIntensity(5)
    setTrigger('')
    setNotes('')
  }

  const getMoodColor = (mood: string) => {
    const moodOption = MOOD_OPTIONS.find(m => m.value === mood)
    return moodOption?.color || '#6b7280'
  }

  const getMoodLabel = (mood: string) => {
    const moodOption = MOOD_OPTIONS.find(m => m.value === mood)
    return moodOption?.label || mood
  }

  const getTrendIcon = (trend: string) => {
    if (trend === 'improving') return <TrendingUp className="text-green-500" size={24} />
    if (trend === 'declining') return <TrendingDown className="text-red-500" size={24} />
    return <Minus className="text-gray-500" size={24} />
  }

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const hours = Math.floor(diff / 3600000)

    if (hours < 1) return 'Przed chwilą'
    if (hours < 24) return `${hours}h temu`
    return date.toLocaleDateString('pl-PL', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
  }

  // Prepare chart data
  const chartData = entries.slice(0, 14).reverse().map(entry => ({
    date: new Date(entry.timestamp).toLocaleDateString('pl-PL', { month: 'short', day: 'numeric' }),
    intensity: entry.intensity,
    mood: entry.mood,
    trigger: entry.trigger
  }))

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 p-6 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="animate-spin text-purple-500" size={48} />
          <p className="text-gray-600 dark:text-gray-400">Ładowanie danych nastroju...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 p-6">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold gradient-text mb-2">💭 Mood Tracker v2.0</h1>
            <p className="text-gray-600 dark:text-gray-400">
              Śledź swój nastrój · Wsparcie CBT/DBT · Analiza wzorców emocjonalnych
            </p>
          </div>
          <Link
            href="/"
            className="px-4 py-2 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-lg hover:from-purple-600 hover:to-blue-600 transition-all shadow-lg"
          >
            💬 Chat
          </Link>
        </div>
      </div>

      <div className="max-w-7xl mx-auto space-y-6">
        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-gray-200 dark:border-slate-700">
              <div className="flex items-center justify-between mb-2">
                <div className="p-3 rounded-lg bg-gradient-to-br from-purple-500 to-purple-600 text-white">
                  <Heart size={24} />
                </div>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Wpisy</p>
              <p className="text-2xl font-bold text-gray-800 dark:text-gray-200">{stats.total_entries}</p>
            </div>

            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-gray-200 dark:border-slate-700">
              <div className="flex items-center justify-between mb-2">
                <div className="p-3 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 text-white">
                  <Sparkles size={24} />
                </div>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Średnia intensywność</p>
              <p className="text-2xl font-bold text-gray-800 dark:text-gray-200">{stats.average_intensity.toFixed(1)}/10</p>
            </div>

            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-gray-200 dark:border-slate-700">
              <div className="flex items-center justify-between mb-2">
                <div className="p-3 rounded-lg bg-gradient-to-br from-pink-500 to-pink-600 text-white">
                  <Calendar size={24} />
                </div>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Najczęstszy nastrój</p>
              <p className="text-xl font-bold text-gray-800 dark:text-gray-200 capitalize">{getMoodLabel(stats.most_common_mood)}</p>
            </div>

            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-gray-200 dark:border-slate-700">
              <div className="flex items-center justify-between mb-2">
                <div className="p-3 rounded-lg bg-gradient-to-br from-green-500 to-green-600 text-white">
                  {getTrendIcon(stats.trend)}
                </div>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Trend</p>
              <p className="text-xl font-bold text-gray-800 dark:text-gray-200 capitalize">
                {stats.trend === 'improving' ? '📈 Poprawia się' : stats.trend === 'declining' ? '📉 Pogarsza się' : '➡️ Stabilny'}
              </p>
            </div>
          </div>
        )}

        {/* Add Mood Button */}
        {!showAddMood && (
          <button
            onClick={() => setShowAddMood(true)}
            className="w-full flex items-center justify-center gap-2 px-6 py-4 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-2xl hover:from-purple-600 hover:to-blue-600 transition-all shadow-lg font-medium"
          >
            <Plus size={24} />
            <span>Jak się dzisiaj czujesz?</span>
          </button>
        )}

        {/* Add Mood Form */}
        {showAddMood && (
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-gray-200 dark:border-slate-700">
            <h3 className="text-xl font-semibold mb-4 text-gray-800 dark:text-gray-200">
              💭 Zapisz swój nastrój
            </h3>

            {/* Mood Selection */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                Wybierz nastrój
              </label>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {MOOD_OPTIONS.map((mood) => (
                  <button
                    key={mood.value}
                    onClick={() => setSelectedMood(mood.value)}
                    className={`p-4 rounded-xl border-2 transition-all text-center ${
                      selectedMood === mood.value
                        ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20 shadow-md'
                        : 'border-gray-200 dark:border-slate-700 hover:border-purple-300 dark:hover:border-purple-700'
                    }`}
                  >
                    <div className="text-3xl mb-1">{mood.label.split(' ')[0]}</div>
                    <div className="text-xs font-medium text-gray-700 dark:text-gray-300">
                      {mood.label.split(' ').slice(1).join(' ')}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Intensity Slider */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                Intensywność: <span className="text-purple-600 font-bold">{intensity}/10</span>
              </label>
              <input
                type="range"
                min="1"
                max="10"
                value={intensity}
                onChange={(e) => setIntensity(Number(e.target.value))}
                className="w-full h-2 bg-gray-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-purple-500"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>Słabo</span>
                <span>Średnio</span>
                <span>Bardzo silnie</span>
              </div>
            </div>

            {/* Trigger */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Co wywołało ten nastrój? (opcjonalnie)
              </label>
              <input
                type="text"
                value={trigger}
                onChange={(e) => setTrigger(e.target.value)}
                placeholder="np. rozmowa, praca, wydarzenie..."
                className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-purple-500 outline-none"
              />
            </div>

            {/* Notes */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Notatki (opcjonalnie)
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Dodatkowe myśli, uczucia, obserwacje..."
                rows={3}
                className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-purple-500 outline-none resize-none"
              />
            </div>

            {/* Buttons */}
            <div className="flex gap-3">
              <button
                onClick={addMoodEntry}
                className="flex-1 px-6 py-3 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-xl hover:from-purple-600 hover:to-blue-600 transition-all font-medium"
              >
                Zapisz Nastrój
              </button>
              <button
                onClick={() => {
                  setShowAddMood(false)
                  resetMoodForm()
                }}
                className="px-6 py-3 bg-gray-200 dark:bg-slate-700 text-gray-700 dark:text-gray-300 rounded-xl hover:bg-gray-300 dark:hover:bg-slate-600 transition-all font-medium"
              >
                Anuluj
              </button>
            </div>
          </div>
        )}

        {/* Mood Timeline Chart */}
        {entries.length > 0 && (
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-gray-200 dark:border-slate-700">
            <h2 className="text-xl font-semibold mb-4 text-gray-800 dark:text-gray-200">
              📈 Timeline Nastroju (ostatnie 14 dni)
            </h2>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 12 }}
                />
                <YAxis domain={[0, 10]} />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload
                      return (
                        <div className="bg-white dark:bg-slate-800 p-3 rounded-lg shadow-lg border">
                          <p className="font-semibold">{data.date}</p>
                          <p>Nastrój: {getMoodLabel(data.mood)}</p>
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
          </div>
        )}

        {/* Mood Entries List */}
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-gray-200 dark:border-slate-700">
          <h2 className="text-xl font-semibold mb-4 text-gray-800 dark:text-gray-200">
            📝 Historia Nastrojów
          </h2>

          {entries.length === 0 ? (
            <div className="text-center py-12">
              <Heart size={64} className="mx-auto mb-4 text-gray-400" />
              <h3 className="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-2">
                Brak wpisów
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Zacznij śledzić swój nastrój, aby zobaczyć wzorce i trendy!
              </p>
            </div>
          ) : (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {entries.map((entry) => (
                <div
                  key={entry.mood_id}
                  className="p-4 rounded-xl border border-gray-200 dark:border-slate-700 hover:shadow-md transition-shadow"
                  style={{
                    borderLeftWidth: '4px',
                    borderLeftColor: getMoodColor(entry.mood)
                  }}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-2xl">{getMoodLabel(entry.mood).split(' ')[0]}</span>
                        <span className="font-semibold text-gray-800 dark:text-gray-200">
                          {getMoodLabel(entry.mood).split(' ').slice(1).join(' ')}
                        </span>
                        <span className="px-2 py-1 bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400 rounded-lg text-xs font-medium">
                          {entry.intensity}/10
                        </span>
                      </div>
                      {entry.trigger && (
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                          🎯 Trigger: {entry.trigger}
                        </p>
                      )}
                      {entry.notes && (
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          💬 {entry.notes}
                        </p>
                      )}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 text-right">
                      {formatTimestamp(entry.timestamp)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* CBT/DBT Tips */}
        <div className="bg-gradient-to-r from-purple-500 to-blue-500 rounded-2xl shadow-lg p-6 text-white">
          <h2 className="text-xl font-semibold mb-4">💡 Wskazówki CBT/DBT</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-white/20 backdrop-blur-sm rounded-lg p-4">
              <p className="font-semibold mb-1">🧠 Cognitive Behavioral Therapy</p>
              <p className="text-sm opacity-90">
                Zwracaj uwagę na wzorce myślowe. Jak Twoje myśli wpływają na nastrój?
              </p>
            </div>
            <div className="bg-white/20 backdrop-blur-sm rounded-lg p-4">
              <p className="font-semibold mb-1">🎯 Dialectical Behavior Therapy</p>
              <p className="text-sm opacity-90">
                Praktykuj uważność. Akceptuj emocje bez oceniania ich.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
