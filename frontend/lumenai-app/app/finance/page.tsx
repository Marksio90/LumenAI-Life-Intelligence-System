'use client'

import { useEffect, useState } from 'react'
import { useChatStore } from '@/lib/store'
import { DollarSign, Plus, TrendingUp, TrendingDown, PieChart, BarChart3, Calendar, Trash2, Loader2, ArrowUpRight, ArrowDownRight } from 'lucide-react'
import { BarChart, Bar, PieChart as RePieChart, Pie, Cell, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import Link from 'next/link'

interface Expense {
  expense_id: string
  amount: number
  category: string
  description?: string
  date: string
  created_at: string
}

interface Budget {
  budget_id: string
  category: string
  limit: number
  spent: number
  period: 'daily' | 'weekly' | 'monthly'
}

interface FinancialStats {
  total_expenses: number
  total_income: number
  balance: number
  expenses_this_month: number
  expenses_last_month: number
  trend: 'increasing' | 'decreasing' | 'stable'
  top_categories: Array<{ category: string; amount: number; percentage: number; color: string }>
}

const EXPENSE_CATEGORIES = [
  { value: 'food', label: '🍔 Jedzenie', color: '#10b981' },
  { value: 'transport', label: '🚗 Transport', color: '#3b82f6' },
  { value: 'entertainment', label: '🎬 Rozrywka', color: '#ec4899' },
  { value: 'shopping', label: '🛍️ Zakupy', color: '#f59e0b' },
  { value: 'health', label: '💊 Zdrowie', color: '#ef4444' },
  { value: 'bills', label: '📄 Rachunki', color: '#8b5cf6' },
  { value: 'education', label: '📚 Edukacja', color: '#14b8a6' },
  { value: 'other', label: '📦 Inne', color: '#6b7280' }
]

export default function FinancePage() {
  const { userId, addToast } = useChatStore()
  const [expenses, setExpenses] = useState<Expense[]>([])
  const [budgets, setBudgets] = useState<Budget[]>([])
  const [stats, setStats] = useState<FinancialStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [showAddExpense, setShowAddExpense] = useState(false)
  const [showAddBudget, setShowAddBudget] = useState(false)
  const [activeTab, setActiveTab] = useState<'expenses' | 'budgets' | 'analytics'>('expenses')

  // New expense form
  const [newExpenseAmount, setNewExpenseAmount] = useState('')
  const [newExpenseCategory, setNewExpenseCategory] = useState('food')
  const [newExpenseDescription, setNewExpenseDescription] = useState('')
  const [newExpenseDate, setNewExpenseDate] = useState(new Date().toISOString().split('T')[0])

  // New budget form
  const [newBudgetCategory, setNewBudgetCategory] = useState('food')
  const [newBudgetLimit, setNewBudgetLimit] = useState('')
  const [newBudgetPeriod, setNewBudgetPeriod] = useState<'daily' | 'weekly' | 'monthly'>('monthly')

  useEffect(() => {
    fetchFinanceData()
  }, [userId])

  const fetchFinanceData = async () => {
    setLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

      // Fetch expenses
      const expensesRes = await fetch(`${apiUrl}/api/v1/finance/${userId}/expenses?limit=50`)
      const expensesData = await expensesRes.json()

      if (expensesData.status === 'success') {
        setExpenses(expensesData.expenses || [])
      }

      // Fetch budgets
      const budgetsRes = await fetch(`${apiUrl}/api/v1/finance/${userId}/budgets`)
      const budgetsData = await budgetsRes.json()

      if (budgetsData.status === 'success') {
        setBudgets(budgetsData.budgets || [])
      }

      // Fetch stats
      const statsRes = await fetch(`${apiUrl}/api/v1/finance/${userId}/stats`)
      const statsData = await statsRes.json()

      if (statsData.status === 'success') {
        setStats(statsData.stats)
      }
    } catch (error) {
      console.error('Error fetching finance data:', error)
      addToast({
        message: 'Nie udało się załadować danych finansowych',
        type: 'error'
      })
    } finally {
      setLoading(false)
    }
  }

  const addExpense = async () => {
    if (!newExpenseAmount || parseFloat(newExpenseAmount) <= 0) {
      addToast({
        message: 'Wprowadź prawidłową kwotę',
        type: 'error'
      })
      return
    }

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/v1/finance/${userId}/expenses`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount: parseFloat(newExpenseAmount),
          category: newExpenseCategory,
          description: newExpenseDescription || null,
          date: newExpenseDate
        })
      })

      const data = await response.json()

      if (data.status === 'success') {
        addToast({
          message: '✅ Wydatek dodany!',
          type: 'success'
        })
        setShowAddExpense(false)
        resetExpenseForm()
        await fetchFinanceData()
      }
    } catch (error) {
      console.error('Error adding expense:', error)
      addToast({
        message: 'Nie udało się dodać wydatku',
        type: 'error'
      })
    }
  }

  const deleteExpense = async (expenseId: string) => {
    if (!confirm('Czy na pewno chcesz usunąć ten wydatek?')) return

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/v1/finance/${userId}/expenses/${expenseId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        addToast({
          message: 'Wydatek usunięty',
          type: 'success'
        })
        await fetchFinanceData()
      }
    } catch (error) {
      console.error('Error deleting expense:', error)
    }
  }

  const addBudget = async () => {
    if (!newBudgetLimit || parseFloat(newBudgetLimit) <= 0) {
      addToast({
        message: 'Wprowadź prawidłowy limit',
        type: 'error'
      })
      return
    }

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/v1/finance/${userId}/budgets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category: newBudgetCategory,
          limit: parseFloat(newBudgetLimit),
          period: newBudgetPeriod
        })
      })

      const data = await response.json()

      if (data.status === 'success') {
        addToast({
          message: '✅ Budget utworzony!',
          type: 'success'
        })
        setShowAddBudget(false)
        resetBudgetForm()
        await fetchFinanceData()
      }
    } catch (error) {
      console.error('Error adding budget:', error)
      addToast({
        message: 'Nie udało się utworzyć budgetu',
        type: 'error'
      })
    }
  }

  const resetExpenseForm = () => {
    setNewExpenseAmount('')
    setNewExpenseCategory('food')
    setNewExpenseDescription('')
    setNewExpenseDate(new Date().toISOString().split('T')[0])
  }

  const resetBudgetForm = () => {
    setNewBudgetCategory('food')
    setNewBudgetLimit('')
    setNewBudgetPeriod('monthly')
  }

  const getCategoryLabel = (category: string) => {
    return EXPENSE_CATEGORIES.find(c => c.value === category)?.label || category
  }

  const getCategoryColor = (category: string) => {
    return EXPENSE_CATEGORIES.find(c => c.value === category)?.color || '#6b7280'
  }

  const formatCurrency = (amount: number) => {
    return `${amount.toFixed(2)} PLN`
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('pl-PL', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    })
  }

  // Prepare chart data
  const expensesByCategory = stats?.top_categories || []
  const recentExpenses = expenses.slice(0, 10).reverse()

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 p-6 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="animate-spin text-purple-500" size={48} />
          <p className="text-gray-600 dark:text-gray-400">Ładowanie danych finansowych...</p>
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
            <h1 className="text-3xl font-bold gradient-text mb-2">💰 Finance Tracker v2.0</h1>
            <p className="text-gray-600 dark:text-gray-400">
              Śledź wydatki · Zarządzaj budżetem · Analityka finansowa
              <span className="ml-2 px-2 py-1 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300 text-xs rounded-lg font-medium">
                Beta
              </span>
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
              <div className="flex items-start justify-between mb-2">
                <div className="p-3 rounded-lg bg-gradient-to-br from-red-500 to-red-600 text-white">
                  <ArrowUpRight size={24} />
                </div>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Wydatki ogółem</p>
              <p className="text-2xl font-bold text-gray-800 dark:text-gray-200">{formatCurrency(stats.total_expenses)}</p>
            </div>

            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-gray-200 dark:border-slate-700">
              <div className="flex items-start justify-between mb-2">
                <div className="p-3 rounded-lg bg-gradient-to-br from-green-500 to-green-600 text-white">
                  <ArrowDownRight size={24} />
                </div>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Przychód</p>
              <p className="text-2xl font-bold text-gray-800 dark:text-gray-200">{formatCurrency(stats.total_income)}</p>
            </div>

            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-gray-200 dark:border-slate-700">
              <div className="flex items-start justify-between mb-2">
                <div className="p-3 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 text-white">
                  <DollarSign size={24} />
                </div>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Bilans</p>
              <p className={`text-2xl font-bold ${stats.balance >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatCurrency(stats.balance)}
              </p>
            </div>

            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-gray-200 dark:border-slate-700">
              <div className="flex items-start justify-between mb-2">
                <div className="p-3 rounded-lg bg-gradient-to-br from-purple-500 to-purple-600 text-white">
                  {stats.trend === 'increasing' ? <TrendingUp size={24} /> : stats.trend === 'decreasing' ? <TrendingDown size={24} /> : <BarChart3 size={24} />}
                </div>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Ten miesiąc</p>
              <p className="text-2xl font-bold text-gray-800 dark:text-gray-200">{formatCurrency(stats.expenses_this_month)}</p>
              <p className="text-xs text-gray-500 mt-1">
                vs {formatCurrency(stats.expenses_last_month)} w zeszłym miesiącu
              </p>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab('expenses')}
            className={`px-6 py-3 rounded-xl font-medium transition-all ${
              activeTab === 'expenses'
                ? 'bg-gradient-to-r from-purple-500 to-blue-500 text-white shadow-lg'
                : 'bg-white dark:bg-slate-800 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-700'
            }`}
          >
            💳 Wydatki ({expenses.length})
          </button>
          <button
            onClick={() => setActiveTab('budgets')}
            className={`px-6 py-3 rounded-xl font-medium transition-all ${
              activeTab === 'budgets'
                ? 'bg-gradient-to-r from-purple-500 to-blue-500 text-white shadow-lg'
                : 'bg-white dark:bg-slate-800 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-700'
            }`}
          >
            🎯 Budżety ({budgets.length})
          </button>
          <button
            onClick={() => setActiveTab('analytics')}
            className={`px-6 py-3 rounded-xl font-medium transition-all ${
              activeTab === 'analytics'
                ? 'bg-gradient-to-r from-purple-500 to-blue-500 text-white shadow-lg'
                : 'bg-white dark:bg-slate-800 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-700'
            }`}
          >
            📊 Analityka
          </button>
        </div>

        {/* Expenses Tab */}
        {activeTab === 'expenses' && (
          <div className="space-y-6">
            {!showAddExpense && (
              <button
                onClick={() => setShowAddExpense(true)}
                className="w-full flex items-center justify-center gap-2 px-6 py-4 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-2xl hover:from-purple-600 hover:to-blue-600 transition-all shadow-lg font-medium"
              >
                <Plus size={24} />
                <span>Dodaj Wydatek</span>
              </button>
            )}

            {showAddExpense && (
              <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-gray-200 dark:border-slate-700">
                <h3 className="text-xl font-semibold mb-4 text-gray-800 dark:text-gray-200">
                  💰 Nowy Wydatek
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Kwota (PLN) *
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      value={newExpenseAmount}
                      onChange={(e) => setNewExpenseAmount(e.target.value)}
                      placeholder="0.00"
                      className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-purple-500 outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Kategoria *
                    </label>
                    <select
                      value={newExpenseCategory}
                      onChange={(e) => setNewExpenseCategory(e.target.value)}
                      className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-purple-500 outline-none"
                    >
                      {EXPENSE_CATEGORIES.map((cat) => (
                        <option key={cat.value} value={cat.value}>
                          {cat.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Data
                    </label>
                    <input
                      type="date"
                      value={newExpenseDate}
                      onChange={(e) => setNewExpenseDate(e.target.value)}
                      className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-purple-500 outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Opis
                    </label>
                    <input
                      type="text"
                      value={newExpenseDescription}
                      onChange={(e) => setNewExpenseDescription(e.target.value)}
                      placeholder="np. Zakupy spożywcze"
                      className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-purple-500 outline-none"
                    />
                  </div>
                </div>

                <div className="flex gap-3 mt-4">
                  <button
                    onClick={addExpense}
                    className="flex-1 px-6 py-3 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-xl hover:from-purple-600 hover:to-blue-600 transition-all font-medium"
                  >
                    Dodaj Wydatek
                  </button>
                  <button
                    onClick={() => {
                      setShowAddExpense(false)
                      resetExpenseForm()
                    }}
                    className="px-6 py-3 bg-gray-200 dark:bg-slate-700 text-gray-700 dark:text-gray-300 rounded-xl hover:bg-gray-300 dark:hover:bg-slate-600 transition-all font-medium"
                  >
                    Anuluj
                  </button>
                </div>
              </div>
            )}

            {/* Expenses List */}
            {expenses.length === 0 ? (
              <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-12 border border-gray-200 dark:border-slate-700 text-center">
                <DollarSign size={64} className="mx-auto mb-4 text-gray-400" />
                <h3 className="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-2">
                  Brak wydatków
                </h3>
                <p className="text-gray-600 dark:text-gray-400">
                  Dodaj swój pierwszy wydatek, aby rozpocząć śledzenie finansów!
                </p>
              </div>
            ) : (
              <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-gray-200 dark:border-slate-700">
                <h3 className="text-lg font-semibold mb-4 text-gray-800 dark:text-gray-200">
                  Ostatnie wydatki
                </h3>
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {expenses.map((expense) => (
                    <div
                      key={expense.expense_id}
                      className="flex items-center justify-between p-4 rounded-xl border border-gray-200 dark:border-slate-700 hover:shadow-md transition-shadow"
                    >
                      <div className="flex items-center gap-4">
                        <div
                          className="w-10 h-10 rounded-lg flex items-center justify-center text-white font-bold"
                          style={{ backgroundColor: getCategoryColor(expense.category) }}
                        >
                          {getCategoryLabel(expense.category).split(' ')[0]}
                        </div>
                        <div>
                          <p className="font-medium text-gray-800 dark:text-gray-200">
                            {expense.description || getCategoryLabel(expense.category)}
                          </p>
                          <p className="text-sm text-gray-500 dark:text-gray-400">
                            {formatDate(expense.date)}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <p className="text-lg font-bold text-red-600">
                          -{formatCurrency(expense.amount)}
                        </p>
                        <button
                          onClick={() => deleteExpense(expense.expense_id)}
                          className="p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-all"
                        >
                          <Trash2 size={18} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Budgets Tab */}
        {activeTab === 'budgets' && (
          <div className="space-y-6">
            {!showAddBudget && (
              <button
                onClick={() => setShowAddBudget(true)}
                className="w-full flex items-center justify-center gap-2 px-6 py-4 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-2xl hover:from-purple-600 hover:to-blue-600 transition-all shadow-lg font-medium"
              >
                <Plus size={24} />
                <span>Dodaj Budget</span>
              </button>
            )}

            {showAddBudget && (
              <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-gray-200 dark:border-slate-700">
                <h3 className="text-xl font-semibold mb-4 text-gray-800 dark:text-gray-200">
                  🎯 Nowy Budget
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Kategoria
                    </label>
                    <select
                      value={newBudgetCategory}
                      onChange={(e) => setNewBudgetCategory(e.target.value)}
                      className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-purple-500 outline-none"
                    >
                      {EXPENSE_CATEGORIES.map((cat) => (
                        <option key={cat.value} value={cat.value}>
                          {cat.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Limit (PLN)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      value={newBudgetLimit}
                      onChange={(e) => setNewBudgetLimit(e.target.value)}
                      placeholder="0.00"
                      className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-purple-500 outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Okres
                    </label>
                    <select
                      value={newBudgetPeriod}
                      onChange={(e) => setNewBudgetPeriod(e.target.value as any)}
                      className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-purple-500 outline-none"
                    >
                      <option value="daily">Dzienny</option>
                      <option value="weekly">Tygodniowy</option>
                      <option value="monthly">Miesięczny</option>
                    </select>
                  </div>
                </div>

                <div className="flex gap-3 mt-4">
                  <button
                    onClick={addBudget}
                    className="flex-1 px-6 py-3 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-xl hover:from-purple-600 hover:to-blue-600 transition-all font-medium"
                  >
                    Utwórz Budget
                  </button>
                  <button
                    onClick={() => {
                      setShowAddBudget(false)
                      resetBudgetForm()
                    }}
                    className="px-6 py-3 bg-gray-200 dark:bg-slate-700 text-gray-700 dark:text-gray-300 rounded-xl hover:bg-gray-300 dark:hover:bg-slate-600 transition-all font-medium"
                  >
                    Anuluj
                  </button>
                </div>
              </div>
            )}

            {/* Budgets List */}
            {budgets.length === 0 ? (
              <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-12 border border-gray-200 dark:border-slate-700 text-center">
                <PieChart size={64} className="mx-auto mb-4 text-gray-400" />
                <h3 className="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-2">
                  Brak budżetów
                </h3>
                <p className="text-gray-600 dark:text-gray-400">
                  Ustaw budżety dla różnych kategorii wydatków!
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {budgets.map((budget) => {
                  const percentage = (budget.spent / budget.limit) * 100
                  const isOverBudget = percentage > 100

                  return (
                    <div
                      key={budget.budget_id}
                      className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-gray-200 dark:border-slate-700"
                    >
                      <div className="flex items-center justify-between mb-4">
                        <h4 className="font-semibold text-gray-800 dark:text-gray-200">
                          {getCategoryLabel(budget.category)}
                        </h4>
                        <span className="text-xs text-gray-500 capitalize">
                          {budget.period === 'daily' ? 'Dzienny' : budget.period === 'weekly' ? 'Tygodniowy' : 'Miesięczny'}
                        </span>
                      </div>

                      <div className="mb-2">
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-gray-600 dark:text-gray-400">
                            {formatCurrency(budget.spent)} / {formatCurrency(budget.limit)}
                          </span>
                          <span className={`font-bold ${isOverBudget ? 'text-red-600' : 'text-green-600'}`}>
                            {percentage.toFixed(0)}%
                          </span>
                        </div>
                        <div className="w-full h-3 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
                          <div
                            className={`h-full transition-all ${
                              isOverBudget ? 'bg-red-500' : percentage > 80 ? 'bg-yellow-500' : 'bg-green-500'
                            }`}
                            style={{ width: `${Math.min(percentage, 100)}%` }}
                          />
                        </div>
                      </div>

                      {isOverBudget && (
                        <p className="text-xs text-red-600 font-medium mt-2">
                          ⚠️ Przekroczono budget o {formatCurrency(budget.spent - budget.limit)}
                        </p>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}

        {/* Analytics Tab */}
        {activeTab === 'analytics' && stats && (
          <div className="space-y-6">
            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-gray-200 dark:border-slate-700">
              <h3 className="text-xl font-semibold mb-4 text-gray-800 dark:text-gray-200">
                📊 Wydatki po Kategoriach
              </h3>
              {expensesByCategory.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <RePieChart>
                    <Pie
                      data={expensesByCategory}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={(entry: any) => `${entry.category}: ${entry.percentage}%`}
                      outerRadius={100}
                      fill="#8884d8"
                      dataKey="amount"
                    >
                      {expensesByCategory.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </RePieChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-center text-gray-500 py-12">Brak danych do wyświetlenia</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
