'use client'

import { useEffect, useState } from 'react'
import { Activity, Database, Zap, CheckCircle, XCircle, AlertCircle, Loader2 } from 'lucide-react'
import Link from 'next/link'

interface ServiceStatus {
  name: string
  status: 'healthy' | 'degraded' | 'down'
  responseTime?: number
  lastCheck?: string
}

export default function HealthDashboard() {
  const [services, setServices] = useState<ServiceStatus[]>([])
  const [loading, setLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())

  useEffect(() => {
    checkHealth()
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  const checkHealth = async () => {
    setLoading(true)
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const healthChecks: ServiceStatus[] = []

    try {
      const start = Date.now()
      const res = await fetch(`${apiUrl}/health`)
      const responseTime = Date.now() - start
      healthChecks.push({
        name: 'Backend API',
        status: res.ok ? 'healthy' : 'down',
        responseTime,
        lastCheck: new Date().toISOString()
      })
    } catch {
      healthChecks.push({ name: 'Backend API', status: 'down', lastCheck: new Date().toISOString() })
    }

    try {
      await fetch(`${apiUrl}/api/v1/user/health/check`)
      healthChecks.push({ name: 'MongoDB', status: 'healthy', lastCheck: new Date().toISOString() })
    } catch {
      healthChecks.push({ name: 'MongoDB', status: 'down', lastCheck: new Date().toISOString() })
    }

    setServices(healthChecks)
    setLastUpdate(new Date())
    setLoading(false)
  }

  const overallHealth = services.every(s => s.status === 'healthy') ? 'healthy' : 'degraded'

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 p-6">
      <div className="max-w-7xl mx-auto mb-8">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold gradient-text mb-2">🏥 System Health</h1>
            <p className="text-gray-600 dark:text-gray-400">Real-time monitoring · Auto-refresh every 30s</p>
          </div>
          <Link href="/" className="px-4 py-2 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-lg hover:from-purple-600 hover:to-blue-600 transition-all shadow-lg">
            💬 Chat
          </Link>
        </div>
      </div>

      <div className="max-w-7xl mx-auto space-y-6">
        <div className={`rounded-2xl shadow-lg p-6 border ${overallHealth === 'healthy' ? 'bg-green-50 dark:bg-green-900/20 border-green-200' : 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200'}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {overallHealth === 'healthy' ? <CheckCircle className="text-green-500" size={32} /> : <AlertCircle className="text-yellow-500" size={32} />}
              <div>
                <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-200">
                  {overallHealth === 'healthy' ? 'All Systems Operational ✅' : 'Some Issues Detected ⚠️'}
                </h2>
                <p className="text-sm text-gray-600 dark:text-gray-400">Last updated: {lastUpdate.toLocaleTimeString('pl-PL')}</p>
              </div>
            </div>
            <button onClick={checkHealth} disabled={loading} className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 transition-all border">
              {loading ? <Loader2 className="animate-spin" size={18} /> : <Activity size={18} />}
              <span>Refresh</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {services.map((service) => (
            <div key={service.name} className={`rounded-2xl shadow-lg p-6 border ${service.status === 'healthy' ? 'bg-green-50 dark:bg-green-900/20 border-green-200' : 'bg-red-50 dark:bg-red-900/20 border-red-200'}`}>
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  {service.name.includes('MongoDB') ? <Database size={24} /> : service.name.includes('Backend') ? <Activity size={24} /> : <Zap size={24} />}
                  <h3 className="font-semibold text-gray-800 dark:text-gray-200">{service.name}</h3>
                </div>
                {service.status === 'healthy' ? <CheckCircle className="text-green-500" size={24} /> : <XCircle className="text-red-500" size={24} />}
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Status:</span>
                  <span className="font-medium capitalize">{service.status}</span>
                </div>
                {service.responseTime && (
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Response Time:</span>
                    <span className="font-medium">{service.responseTime}ms</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
