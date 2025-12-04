'use client'

import { useEffect, useState } from 'react'
import { useChatStore } from '@/lib/store'
import { Brain, Plus, ThumbsUp, ThumbsDown, Lightbulb, TrendingUp, Check, X, Loader2, MessageSquare } from 'lucide-react'
import Link from 'next/link'

interface Decision {
  decision_id: string
  title: string
  description?: string
  options: DecisionOption[]
  analysis?: {
    recommendation: string
    reasoning: string
    risk_level: 'low' | 'medium' | 'high'
  }
  status: 'pending' | 'analyzed' | 'decided'
  final_choice?: string
  created_at: string
  updated_at: string
}

interface DecisionOption {
  option_id: string
  name: string
  pros: string[]
  cons: string[]
  score?: number
}

export default function DecisionsPage() {
  const { userId, addToast } = useChatStore()
  const [decisions, setDecisions] = useState<Decision[]>([])
  const [loading, setLoading] = useState(true)
  const [showAddDecision, setShowAddDecision] = useState(false)
  const [analyzing, setAnalyzing] = useState<string | null>(null)

  // New decision form state
  const [newDecisionTitle, setNewDecisionTitle] = useState('')
  const [newDecisionDescription, setNewDecisionDescription] = useState('')
  const [options, setOptions] = useState<Array<{ name: string; pros: string[]; cons: string[] }>>([
    { name: '', pros: [''], cons: [''] },
    { name: '', pros: [''], cons: [''] }
  ])

  useEffect(() => {
    fetchDecisions()
  }, [userId])

  const fetchDecisions = async () => {
    setLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/v1/decisions/${userId}?limit=20`)
      const data = await response.json()

      if (data.status === 'success') {
        setDecisions(data.decisions || [])
      }
    } catch (error) {
      console.error('Error fetching decisions:', error)
      addToast({
        message: 'Nie udało się załadować decyzji',
        type: 'error'
      })
    } finally {
      setLoading(false)
    }
  }

  const createDecision = async () => {
    if (!newDecisionTitle.trim()) {
      addToast({
        message: 'Tytuł decyzji jest wymagany',
        type: 'error'
      })
      return
    }

    const validOptions = options.filter(opt => opt.name.trim())
    if (validOptions.length < 2) {
      addToast({
        message: 'Dodaj co najmniej 2 opcje',
        type: 'error'
      })
      return
    }

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/v1/decisions/${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: newDecisionTitle,
          description: newDecisionDescription || null,
          options: validOptions.map(opt => ({
            name: opt.name,
            pros: opt.pros.filter(p => p.trim()),
            cons: opt.cons.filter(c => c.trim())
          }))
        })
      })

      const data = await response.json()

      if (data.status === 'success') {
        addToast({
          message: 'Decyzja utworzona!',
          type: 'success'
        })
        setShowAddDecision(false)
        resetDecisionForm()
        await fetchDecisions()
      }
    } catch (error) {
      console.error('Error creating decision:', error)
      addToast({
        message: 'Nie udało się utworzyć decyzji',
        type: 'error'
      })
    }
  }

  const analyzeDecision = async (decisionId: string) => {
    setAnalyzing(decisionId)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/v1/decisions/${userId}/${decisionId}/analyze`, {
        method: 'POST'
      })

      const data = await response.json()

      if (data.status === 'success') {
        addToast({
          message: '✨ Analiza AI ukończona!',
          type: 'success'
        })
        await fetchDecisions()
      }
    } catch (error) {
      console.error('Error analyzing decision:', error)
      addToast({
        message: 'Błąd podczas analizy decyzji',
        type: 'error'
      })
    } finally {
      setAnalyzing(null)
    }
  }

  const markDecided = async (decisionId: string, finalChoice: string) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/v1/decisions/${userId}/${decisionId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          status: 'decided',
          final_choice: finalChoice
        })
      })

      if (response.ok) {
        addToast({
          message: '✅ Decyzja podjęta!',
          type: 'success'
        })
        await fetchDecisions()
      }
    } catch (error) {
      console.error('Error marking decision:', error)
    }
  }

  const resetDecisionForm = () => {
    setNewDecisionTitle('')
    setNewDecisionDescription('')
    setOptions([
      { name: '', pros: [''], cons: [''] },
      { name: '', pros: [''], cons: [''] }
    ])
  }

  const addOption = () => {
    setOptions([...options, { name: '', pros: [''], cons: [''] }])
  }

  const removeOption = (index: number) => {
    if (options.length > 2) {
      setOptions(options.filter((_, i) => i !== index))
    }
  }

  const updateOption = (index: number, field: 'name', value: string) => {
    const updated = [...options]
    updated[index].name = value
    setOptions(updated)
  }

  const addPro = (optionIndex: number) => {
    const updated = [...options]
    updated[optionIndex].pros.push('')
    setOptions(updated)
  }

  const addCon = (optionIndex: number) => {
    const updated = [...options]
    updated[optionIndex].cons.push('')
    setOptions(updated)
  }

  const updatePro = (optionIndex: number, proIndex: number, value: string) => {
    const updated = [...options]
    updated[optionIndex].pros[proIndex] = value
    setOptions(updated)
  }

  const updateCon = (optionIndex: number, conIndex: number, value: string) => {
    const updated = [...options]
    updated[optionIndex].cons[conIndex] = value
    setOptions(updated)
  }

  const removePro = (optionIndex: number, proIndex: number) => {
    const updated = [...options]
    if (updated[optionIndex].pros.length > 1) {
      updated[optionIndex].pros = updated[optionIndex].pros.filter((_, i) => i !== proIndex)
      setOptions(updated)
    }
  }

  const removeCon = (optionIndex: number, conIndex: number) => {
    const updated = [...options]
    if (updated[optionIndex].cons.length > 1) {
      updated[optionIndex].cons = updated[optionIndex].cons.filter((_, i) => i !== conIndex)
      setOptions(updated)
    }
  }

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'high': return 'text-red-600 bg-red-50 dark:bg-red-900/20'
      case 'medium': return 'text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20'
      case 'low': return 'text-green-600 bg-green-50 dark:bg-green-900/20'
      default: return 'text-gray-600 bg-gray-50 dark:bg-gray-900/20'
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 p-6 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="animate-spin text-purple-500" size={48} />
          <p className="text-gray-600 dark:text-gray-400">Ładowanie decyzji...</p>
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
            <h1 className="text-3xl font-bold gradient-text mb-2">🤔 Decision Helper v2.0</h1>
            <p className="text-gray-600 dark:text-gray-400">
              Analiza scenariuszy · Pros/Cons · AI Recommendations
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
        {/* Add Decision Button */}
        {!showAddDecision && (
          <button
            onClick={() => setShowAddDecision(true)}
            className="w-full flex items-center justify-center gap-2 px-6 py-4 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-2xl hover:from-purple-600 hover:to-blue-600 transition-all shadow-lg font-medium"
          >
            <Plus size={24} />
            <span>Nowa Decyzja do Analizy</span>
          </button>
        )}

        {/* Add Decision Form */}
        {showAddDecision && (
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-gray-200 dark:border-slate-700">
            <h3 className="text-xl font-semibold mb-4 text-gray-800 dark:text-gray-200">
              🎯 Nowa Decyzja
            </h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Tytuł decyzji *
                </label>
                <input
                  type="text"
                  value={newDecisionTitle}
                  onChange={(e) => setNewDecisionTitle(e.target.value)}
                  placeholder="np. Czy powinienem zmienić pracę?"
                  className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-purple-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Opis kontekstu
                </label>
                <textarea
                  value={newDecisionDescription}
                  onChange={(e) => setNewDecisionDescription(e.target.value)}
                  placeholder="Opisz sytuację i dlaczego ta decyzja jest ważna..."
                  rows={3}
                  className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-purple-500 outline-none resize-none"
                />
              </div>

              {/* Options */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                  Opcje do rozważenia
                </label>
                <div className="space-y-4">
                  {options.map((option, optIndex) => (
                    <div
                      key={optIndex}
                      className="p-4 bg-gray-50 dark:bg-slate-900 rounded-xl border border-gray-200 dark:border-slate-700"
                    >
                      <div className="flex items-start gap-3 mb-3">
                        <input
                          type="text"
                          value={option.name}
                          onChange={(e) => updateOption(optIndex, 'name', e.target.value)}
                          placeholder={`Opcja ${optIndex + 1}`}
                          className="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-purple-500 outline-none font-medium"
                        />
                        {options.length > 2 && (
                          <button
                            onClick={() => removeOption(optIndex)}
                            className="p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg"
                          >
                            <X size={20} />
                          </button>
                        )}
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {/* Pros */}
                        <div>
                          <div className="flex items-center gap-2 mb-2">
                            <ThumbsUp size={16} className="text-green-600" />
                            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                              Plusy
                            </span>
                          </div>
                          {option.pros.map((pro, proIndex) => (
                            <div key={proIndex} className="flex items-center gap-2 mb-2">
                              <input
                                type="text"
                                value={pro}
                                onChange={(e) => updatePro(optIndex, proIndex, e.target.value)}
                                placeholder="Zaleta..."
                                className="flex-1 px-3 py-2 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-gray-800 dark:text-gray-200 text-sm focus:ring-2 focus:ring-green-500 outline-none"
                              />
                              {option.pros.length > 1 && (
                                <button
                                  onClick={() => removePro(optIndex, proIndex)}
                                  className="p-1 text-gray-400 hover:text-red-600"
                                >
                                  <X size={16} />
                                </button>
                              )}
                            </div>
                          ))}
                          <button
                            onClick={() => addPro(optIndex)}
                            className="text-xs text-green-600 hover:text-green-700 font-medium"
                          >
                            + Dodaj plus
                          </button>
                        </div>

                        {/* Cons */}
                        <div>
                          <div className="flex items-center gap-2 mb-2">
                            <ThumbsDown size={16} className="text-red-600" />
                            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                              Minusy
                            </span>
                          </div>
                          {option.cons.map((con, conIndex) => (
                            <div key={conIndex} className="flex items-center gap-2 mb-2">
                              <input
                                type="text"
                                value={con}
                                onChange={(e) => updateCon(optIndex, conIndex, e.target.value)}
                                placeholder="Wada..."
                                className="flex-1 px-3 py-2 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-gray-800 dark:text-gray-200 text-sm focus:ring-2 focus:ring-red-500 outline-none"
                              />
                              {option.cons.length > 1 && (
                                <button
                                  onClick={() => removeCon(optIndex, conIndex)}
                                  className="p-1 text-gray-400 hover:text-red-600"
                                >
                                  <X size={16} />
                                </button>
                              )}
                            </div>
                          ))}
                          <button
                            onClick={() => addCon(optIndex)}
                            className="text-xs text-red-600 hover:text-red-700 font-medium"
                          >
                            + Dodaj minus
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                <button
                  onClick={addOption}
                  className="mt-3 w-full px-4 py-2 border-2 border-dashed border-gray-300 dark:border-slate-600 text-gray-600 dark:text-gray-400 rounded-lg hover:border-purple-500 hover:text-purple-500 transition-all"
                >
                  + Dodaj kolejną opcję
                </button>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  onClick={createDecision}
                  className="flex-1 px-6 py-3 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-xl hover:from-purple-600 hover:to-blue-600 transition-all font-medium"
                >
                  Utwórz Decyzję
                </button>
                <button
                  onClick={() => {
                    setShowAddDecision(false)
                    resetDecisionForm()
                  }}
                  className="px-6 py-3 bg-gray-200 dark:bg-slate-700 text-gray-700 dark:text-gray-300 rounded-xl hover:bg-gray-300 dark:hover:bg-slate-600 transition-all font-medium"
                >
                  Anuluj
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Decisions List */}
        {decisions.length === 0 ? (
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-12 border border-gray-200 dark:border-slate-700 text-center">
            <Brain size={64} className="mx-auto mb-4 text-gray-400" />
            <h3 className="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-2">
              Brak decyzji do analizy
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              Dodaj swoją pierwszą decyzję i pozwól AI pomóc Ci w wyborze!
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {decisions.map((decision) => (
              <div
                key={decision.decision_id}
                className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-gray-200 dark:border-slate-700"
              >
                {/* Header */}
                <div className="mb-4">
                  <div className="flex items-start justify-between gap-4 mb-2">
                    <h3 className="text-xl font-bold text-gray-800 dark:text-gray-200">
                      {decision.title}
                    </h3>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                      decision.status === 'decided'
                        ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300'
                        : decision.status === 'analyzed'
                        ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300'
                        : 'bg-gray-100 dark:bg-gray-900/30 text-gray-800 dark:text-gray-300'
                    }`}>
                      {decision.status === 'decided' ? '✅ Podjęta' : decision.status === 'analyzed' ? '🤖 Przeanalizowana' : '⏳ Oczekuje'}
                    </span>
                  </div>
                  {decision.description && (
                    <p className="text-gray-600 dark:text-gray-400 text-sm">
                      {decision.description}
                    </p>
                  )}
                </div>

                {/* Options */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                  {decision.options.map((option) => (
                    <div
                      key={option.option_id}
                      className="p-4 bg-gray-50 dark:bg-slate-900 rounded-xl border border-gray-200 dark:border-slate-700"
                    >
                      <h4 className="font-semibold text-gray-800 dark:text-gray-200 mb-3">
                        {option.name}
                        {option.score && (
                          <span className="ml-2 text-sm text-purple-600">
                            ({option.score}/10)
                          </span>
                        )}
                      </h4>

                      <div className="space-y-2 mb-2">
                        <div className="text-sm">
                          <div className="flex items-center gap-1 text-green-600 font-medium mb-1">
                            <ThumbsUp size={14} />
                            <span>Plusy:</span>
                          </div>
                          <ul className="list-disc list-inside text-gray-600 dark:text-gray-400 pl-3">
                            {option.pros.map((pro, i) => (
                              <li key={i}>{pro}</li>
                            ))}
                          </ul>
                        </div>

                        <div className="text-sm">
                          <div className="flex items-center gap-1 text-red-600 font-medium mb-1">
                            <ThumbsDown size={14} />
                            <span>Minusy:</span>
                          </div>
                          <ul className="list-disc list-inside text-gray-600 dark:text-gray-400 pl-3">
                            {option.cons.map((con, i) => (
                              <li key={i}>{con}</li>
                            ))}
                          </ul>
                        </div>
                      </div>

                      {decision.status !== 'decided' && (
                        <button
                          onClick={() => markDecided(decision.decision_id, option.name)}
                          className="w-full mt-2 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-all text-sm font-medium"
                        >
                          ✓ Wybieram tę opcję
                        </button>
                      )}
                    </div>
                  ))}
                </div>

                {/* AI Analysis */}
                {decision.analysis && (
                  <div className="p-4 bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 rounded-xl border border-purple-200 dark:border-purple-800 mb-4">
                    <div className="flex items-start gap-3">
                      <Lightbulb className="text-purple-600 flex-shrink-0 mt-1" size={20} />
                      <div className="flex-1">
                        <h4 className="font-semibold text-gray-800 dark:text-gray-200 mb-2">
                          🤖 Rekomendacja AI
                        </h4>
                        <p className="text-sm text-gray-700 dark:text-gray-300 mb-2 font-medium">
                          {decision.analysis.recommendation}
                        </p>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                          {decision.analysis.reasoning}
                        </p>
                        <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${getRiskColor(decision.analysis.risk_level)}`}>
                          Ryzyko: {decision.analysis.risk_level === 'high' ? '🔴 Wysokie' : decision.analysis.risk_level === 'medium' ? '🟡 Średnie' : '🟢 Niskie'}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-3">
                  {decision.status === 'pending' && (
                    <button
                      onClick={() => analyzeDecision(decision.decision_id)}
                      disabled={analyzing === decision.decision_id}
                      className="flex items-center gap-2 px-6 py-2 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-lg hover:from-purple-600 hover:to-blue-600 transition-all font-medium disabled:opacity-50"
                    >
                      {analyzing === decision.decision_id ? (
                        <>
                          <Loader2 className="animate-spin" size={18} />
                          Analizuję...
                        </>
                      ) : (
                        <>
                          <Brain size={18} />
                          Analizuj z AI
                        </>
                      )}
                    </button>
                  )}

                  {decision.final_choice && (
                    <div className="flex items-center gap-2 px-4 py-2 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 rounded-lg">
                      <Check size={18} />
                      <span className="font-medium">Wybrano: {decision.final_choice}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
