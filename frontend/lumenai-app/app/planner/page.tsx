'use client'

import { useEffect, useState } from 'react'
import { useChatStore } from '@/lib/store'
import { Calendar, Plus, Check, Trash2, Edit2, Clock, Flag, RefreshCw, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react'
import Link from 'next/link'

interface Task {
  task_id: string
  title: string
  description?: string
  due_date?: string
  priority: 'low' | 'medium' | 'high'
  status: 'pending' | 'in_progress' | 'completed'
  category?: string
  created_at: string
  updated_at: string
}

interface CalendarEvent {
  event_id: string
  title: string
  description?: string
  start_time: string
  end_time: string
  location?: string
  attendees?: string[]
}

export default function PlannerPage() {
  const { userId, addToast } = useChatStore()
  const [tasks, setTasks] = useState<Task[]>([])
  const [calendarEvents, setCalendarEvents] = useState<CalendarEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [activeTab, setActiveTab] = useState<'tasks' | 'calendar'>('tasks')
  const [showAddTask, setShowAddTask] = useState(false)
  const [editingTask, setEditingTask] = useState<Task | null>(null)

  // New task form state
  const [newTaskTitle, setNewTaskTitle] = useState('')
  const [newTaskDescription, setNewTaskDescription] = useState('')
  const [newTaskPriority, setNewTaskPriority] = useState<'low' | 'medium' | 'high'>('medium')
  const [newTaskDueDate, setNewTaskDueDate] = useState('')
  const [newTaskCategory, setNewTaskCategory] = useState('')

  // Calendar view state
  const [currentDate, setCurrentDate] = useState(new Date())
  const [viewMode, setViewMode] = useState<'month' | 'week' | 'day'>('month')

  useEffect(() => {
    fetchPlannerData()
  }, [userId])

  const fetchPlannerData = async () => {
    setLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

      // Fetch tasks
      const tasksRes = await fetch(`${apiUrl}/api/v1/planner/${userId}/tasks`)
      const tasksData = await tasksRes.json()

      if (tasksData.status === 'success') {
        setTasks(tasksData.tasks || [])
      }

      // Fetch calendar events
      const eventsRes = await fetch(`${apiUrl}/api/v1/planner/${userId}/calendar/events`)
      const eventsData = await eventsRes.json()

      if (eventsData.status === 'success') {
        setCalendarEvents(eventsData.events || [])
      }
    } catch (error) {
      console.error('Error fetching planner data:', error)
      addToast({
        message: 'Nie udało się załadować danych planera',
        type: 'error'
      })
    } finally {
      setLoading(false)
    }
  }

  const syncGoogleCalendar = async () => {
    setSyncing(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/v1/planner/${userId}/calendar/sync`, {
        method: 'POST'
      })
      const data = await response.json()

      if (data.status === 'success') {
        addToast({
          message: 'Kalendarz zsynchronizowany pomyślnie!',
          type: 'success'
        })
        await fetchPlannerData()
      } else {
        addToast({
          message: 'Błąd synchronizacji kalendarza',
          type: 'error'
        })
      }
    } catch (error) {
      console.error('Error syncing calendar:', error)
      addToast({
        message: 'Wystąpił błąd podczas synchronizacji',
        type: 'error'
      })
    } finally {
      setSyncing(false)
    }
  }

  const createTask = async () => {
    if (!newTaskTitle.trim()) {
      addToast({
        message: 'Tytuł zadania jest wymagany',
        type: 'error'
      })
      return
    }

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/v1/planner/${userId}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: newTaskTitle,
          description: newTaskDescription,
          priority: newTaskPriority,
          due_date: newTaskDueDate || null,
          category: newTaskCategory || null
        })
      })

      const data = await response.json()

      if (data.status === 'success') {
        addToast({
          message: 'Zadanie utworzone!',
          type: 'success'
        })
        setShowAddTask(false)
        resetTaskForm()
        await fetchPlannerData()
      }
    } catch (error) {
      console.error('Error creating task:', error)
      addToast({
        message: 'Nie udało się utworzyć zadania',
        type: 'error'
      })
    }
  }

  const updateTaskStatus = async (taskId: string, status: Task['status']) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/v1/planner/${userId}/tasks/${taskId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
      })

      if (response.ok) {
        await fetchPlannerData()
      }
    } catch (error) {
      console.error('Error updating task:', error)
    }
  }

  const deleteTask = async (taskId: string) => {
    if (!confirm('Czy na pewno chcesz usunąć to zadanie?')) return

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/v1/planner/${userId}/tasks/${taskId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        addToast({
          message: 'Zadanie usunięte',
          type: 'success'
        })
        await fetchPlannerData()
      }
    } catch (error) {
      console.error('Error deleting task:', error)
      addToast({
        message: 'Nie udało się usunąć zadania',
        type: 'error'
      })
    }
  }

  const resetTaskForm = () => {
    setNewTaskTitle('')
    setNewTaskDescription('')
    setNewTaskPriority('medium')
    setNewTaskDueDate('')
    setNewTaskCategory('')
    setEditingTask(null)
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'text-red-600 bg-red-50 dark:bg-red-900/20'
      case 'medium': return 'text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20'
      case 'low': return 'text-green-600 bg-green-50 dark:bg-green-900/20'
      default: return 'text-gray-600 bg-gray-50 dark:bg-gray-900/20'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300'
      case 'in_progress': return 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300'
      case 'pending': return 'bg-gray-100 dark:bg-gray-900/30 text-gray-800 dark:text-gray-300'
      default: return 'bg-gray-100 dark:bg-gray-900/30 text-gray-800 dark:text-gray-300'
    }
  }

  const formatDate = (dateString: string) => {
    if (!dateString) return ''
    const date = new Date(dateString)
    return date.toLocaleDateString('pl-PL', { day: 'numeric', month: 'short', year: 'numeric' })
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 p-6 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="animate-spin text-purple-500" size={48} />
          <p className="text-gray-600 dark:text-gray-400">Ładowanie planera...</p>
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
            <h1 className="text-3xl font-bold gradient-text mb-2">📅 Planner v2.0</h1>
            <p className="text-gray-600 dark:text-gray-400">
              Zarządzaj zadaniami i kalendarzem · Synchronizacja z Google Calendar
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={syncGoogleCalendar}
              disabled={syncing}
              className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 transition-all border border-gray-200 dark:border-slate-700 disabled:opacity-50"
            >
              <RefreshCw className={syncing ? 'animate-spin' : ''} size={18} />
              <span className="hidden sm:inline">Sync Google</span>
            </button>
            <Link
              href="/"
              className="px-4 py-2 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-lg hover:from-purple-600 hover:to-blue-600 transition-all shadow-lg"
            >
              💬 Chat
            </Link>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto">
        {/* Tabs */}
        <div className="flex items-center gap-2 mb-6">
          <button
            onClick={() => setActiveTab('tasks')}
            className={`px-6 py-3 rounded-xl font-medium transition-all ${
              activeTab === 'tasks'
                ? 'bg-gradient-to-r from-purple-500 to-blue-500 text-white shadow-lg'
                : 'bg-white dark:bg-slate-800 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-700'
            }`}
          >
            📝 Zadania ({tasks.length})
          </button>
          <button
            onClick={() => setActiveTab('calendar')}
            className={`px-6 py-3 rounded-xl font-medium transition-all ${
              activeTab === 'calendar'
                ? 'bg-gradient-to-r from-purple-500 to-blue-500 text-white shadow-lg'
                : 'bg-white dark:bg-slate-800 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-700'
            }`}
          >
            📆 Kalendarz ({calendarEvents.length})
          </button>
        </div>

        {/* Tasks Tab */}
        {activeTab === 'tasks' && (
          <div className="space-y-6">
            {/* Add Task Button */}
            {!showAddTask && (
              <button
                onClick={() => setShowAddTask(true)}
                className="w-full flex items-center justify-center gap-2 px-6 py-4 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-2xl hover:from-purple-600 hover:to-blue-600 transition-all shadow-lg font-medium"
              >
                <Plus size={24} />
                <span>Dodaj Nowe Zadanie</span>
              </button>
            )}

            {/* Add Task Form */}
            {showAddTask && (
              <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-gray-200 dark:border-slate-700">
                <h3 className="text-xl font-semibold mb-4 text-gray-800 dark:text-gray-200">
                  ✨ Nowe Zadanie
                </h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Tytuł *
                    </label>
                    <input
                      type="text"
                      value={newTaskTitle}
                      onChange={(e) => setNewTaskTitle(e.target.value)}
                      placeholder="Co chcesz zrobić?"
                      className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-purple-500 outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Opis
                    </label>
                    <textarea
                      value={newTaskDescription}
                      onChange={(e) => setNewTaskDescription(e.target.value)}
                      placeholder="Dodatkowe szczegóły..."
                      rows={3}
                      className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-purple-500 outline-none resize-none"
                    />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Priorytet
                      </label>
                      <select
                        value={newTaskPriority}
                        onChange={(e) => setNewTaskPriority(e.target.value as any)}
                        className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-purple-500 outline-none"
                      >
                        <option value="low">Niski</option>
                        <option value="medium">Średni</option>
                        <option value="high">Wysoki</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Termin
                      </label>
                      <input
                        type="date"
                        value={newTaskDueDate}
                        onChange={(e) => setNewTaskDueDate(e.target.value)}
                        className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-purple-500 outline-none"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Kategoria
                      </label>
                      <input
                        type="text"
                        value={newTaskCategory}
                        onChange={(e) => setNewTaskCategory(e.target.value)}
                        placeholder="np. Praca, Dom"
                        className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-purple-500 outline-none"
                      />
                    </div>
                  </div>

                  <div className="flex gap-3 pt-2">
                    <button
                      onClick={createTask}
                      className="flex-1 px-6 py-3 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-xl hover:from-purple-600 hover:to-blue-600 transition-all font-medium"
                    >
                      Utwórz Zadanie
                    </button>
                    <button
                      onClick={() => {
                        setShowAddTask(false)
                        resetTaskForm()
                      }}
                      className="px-6 py-3 bg-gray-200 dark:bg-slate-700 text-gray-700 dark:text-gray-300 rounded-xl hover:bg-gray-300 dark:hover:bg-slate-600 transition-all font-medium"
                    >
                      Anuluj
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Tasks List */}
            {tasks.length === 0 ? (
              <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-12 border border-gray-200 dark:border-slate-700 text-center">
                <Calendar size={64} className="mx-auto mb-4 text-gray-400" />
                <h3 className="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-2">
                  Brak zadań
                </h3>
                <p className="text-gray-600 dark:text-gray-400">
                  Dodaj swoje pierwsze zadanie, aby rozpocząć planowanie!
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {tasks.map((task) => (
                  <div
                    key={task.task_id}
                    className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-gray-200 dark:border-slate-700 hover:shadow-xl transition-shadow"
                  >
                    <div className="flex items-start gap-4">
                      {/* Status Checkbox */}
                      <button
                        onClick={() => updateTaskStatus(
                          task.task_id,
                          task.status === 'completed' ? 'pending' : 'completed'
                        )}
                        className={`flex-shrink-0 w-6 h-6 rounded-lg border-2 flex items-center justify-center transition-all ${
                          task.status === 'completed'
                            ? 'bg-green-500 border-green-500'
                            : 'border-gray-300 dark:border-slate-600 hover:border-purple-500'
                        }`}
                      >
                        {task.status === 'completed' && <Check size={16} className="text-white" />}
                      </button>

                      {/* Task Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-4 mb-2">
                          <h4 className={`text-lg font-semibold text-gray-800 dark:text-gray-200 ${
                            task.status === 'completed' ? 'line-through opacity-60' : ''
                          }`}>
                            {task.title}
                          </h4>
                          <div className="flex items-center gap-2">
                            <span className={`px-3 py-1 rounded-full text-xs font-medium ${getPriorityColor(task.priority)}`}>
                              {task.priority === 'high' ? '🔴 Wysoki' : task.priority === 'medium' ? '🟡 Średni' : '🟢 Niski'}
                            </span>
                          </div>
                        </div>

                        {task.description && (
                          <p className="text-gray-600 dark:text-gray-400 text-sm mb-3">
                            {task.description}
                          </p>
                        )}

                        <div className="flex flex-wrap items-center gap-3 text-sm text-gray-500 dark:text-gray-400">
                          {task.due_date && (
                            <div className="flex items-center gap-1">
                              <Clock size={14} />
                              <span>{formatDate(task.due_date)}</span>
                            </div>
                          )}
                          {task.category && (
                            <span className="px-2 py-1 bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400 rounded-lg text-xs">
                              {task.category}
                            </span>
                          )}
                          <span className={`px-2 py-1 rounded-lg text-xs ${getStatusColor(task.status)}`}>
                            {task.status === 'completed' ? '✅ Ukończone' : task.status === 'in_progress' ? '🔄 W trakcie' : '⏳ Oczekuje'}
                          </span>
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => deleteTask(task.task_id)}
                          className="p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-all"
                          title="Usuń zadanie"
                        >
                          <Trash2 size={18} />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Calendar Tab */}
        {activeTab === 'calendar' && (
          <div className="space-y-6">
            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-gray-200 dark:border-slate-700">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-semibold text-gray-800 dark:text-gray-200">
                  📆 {currentDate.toLocaleDateString('pl-PL', { month: 'long', year: 'numeric' })}
                </h2>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setCurrentDate(new Date(currentDate.setMonth(currentDate.getMonth() - 1)))}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-all"
                  >
                    <ChevronLeft size={20} />
                  </button>
                  <button
                    onClick={() => setCurrentDate(new Date())}
                    className="px-4 py-2 text-sm font-medium text-purple-600 hover:bg-purple-50 dark:hover:bg-purple-900/20 rounded-lg transition-all"
                  >
                    Dzisiaj
                  </button>
                  <button
                    onClick={() => setCurrentDate(new Date(currentDate.setMonth(currentDate.getMonth() + 1)))}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-all"
                  >
                    <ChevronRight size={20} />
                  </button>
                </div>
              </div>

              {calendarEvents.length === 0 ? (
                <div className="text-center py-12">
                  <Calendar size={64} className="mx-auto mb-4 text-gray-400" />
                  <h3 className="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-2">
                    Brak wydarzeń
                  </h3>
                  <p className="text-gray-600 dark:text-gray-400 mb-4">
                    Zsynchronizuj kalendarz Google, aby zobaczyć swoje wydarzenia
                  </p>
                  <button
                    onClick={syncGoogleCalendar}
                    disabled={syncing}
                    className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-xl hover:from-purple-600 hover:to-blue-600 transition-all font-medium disabled:opacity-50"
                  >
                    <RefreshCw className={syncing ? 'animate-spin' : ''} size={18} />
                    Synchronizuj Kalendarz
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  {calendarEvents.map((event) => (
                    <div
                      key={event.event_id}
                      className="p-4 bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 rounded-xl border border-purple-200 dark:border-purple-800"
                    >
                      <h4 className="font-semibold text-gray-800 dark:text-gray-200 mb-1">
                        {event.title}
                      </h4>
                      {event.description && (
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                          {event.description}
                        </p>
                      )}
                      <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                        <div className="flex items-center gap-1">
                          <Clock size={14} />
                          <span>
                            {new Date(event.start_time).toLocaleString('pl-PL', {
                              hour: '2-digit',
                              minute: '2-digit',
                              day: 'numeric',
                              month: 'short'
                            })}
                          </span>
                        </div>
                        {event.location && (
                          <span className="text-xs">📍 {event.location}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
