'use client'

import { useState } from 'react'
import { useChatStore } from '@/lib/store'
import {
  User, Bell, Palette, Key, Database, Mail, Calendar, FileText,
  CheckSquare, Save, Trash2, Download, Eye, EyeOff
} from 'lucide-react'
import Link from 'next/link'

type TabType = 'profile' | 'integrations' | 'preferences' | 'notifications' | 'api-keys' | 'data'

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabType>('profile')
  const { userId, addToast } = useChatStore(state => ({
    userId: state.userId,
    addToast: state.addToast
  }))

  // Profile state
  const [profile, setProfile] = useState({
    name: '',
    email: '',
    language: 'pl',
    timezone: 'Europe/Warsaw'
  })

  // Integrations state
  const [integrations, setIntegrations] = useState({
    smtp_host: '',
    smtp_port: '587',
    smtp_user: '',
    smtp_password: '',
    google_calendar_enabled: false,
    notion_api_key: '',
    todoist_api_key: '',
    trello_api_key: ''
  })

  // Preferences state
  const [preferences, setPreferences] = useState({
    theme: 'auto',
    language: 'pl',
    compact_mode: false,
    show_agent_names: true,
    animations_enabled: true
  })

  // Notifications state
  const [notifications, setNotifications] = useState({
    email_notifications: true,
    push_notifications: true,
    sound_enabled: true,
    notify_on_response: true,
    notify_on_reminder: true,
    daily_summary: false
  })

  // API Keys state
  const [apiKeys, setApiKeys] = useState({
    openai_key: '',
    openai_model: 'gpt-4o-mini'
  })

  const [showApiKey, setShowApiKey] = useState(false)

  const handleSave = () => {
    // TODO: Save to backend
    addToast({
      message: 'Ustawienia zapisane pomyślnie!',
      type: 'success'
    })
  }

  const handleExportData = () => {
    addToast({
      message: 'Eksport danych rozpoczęty. Otrzymasz powiadomienie gdy będzie gotowy.',
      type: 'info'
    })
  }

  const handleDeleteAccount = () => {
    if (confirm('Czy na pewno chcesz usunąć konto? Ta akcja jest NIEODWRACALNA!')) {
      addToast({
        message: 'Usuwanie konta... Skontaktujemy się z Tobą w celu potwierdzenia.',
        type: 'warning'
      })
    }
  }

  const tabs = [
    { id: 'profile', label: 'Profil', icon: User },
    { id: 'integrations', label: 'Integracje', icon: Database },
    { id: 'preferences', label: 'Preferencje', icon: Palette },
    { id: 'notifications', label: 'Powiadomienia', icon: Bell },
    { id: 'api-keys', label: 'API Keys', icon: Key },
    { id: 'data', label: 'Dane', icon: Database }
  ]

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-950">
      {/* Header */}
      <div className="bg-white dark:bg-slate-900 border-b border-gray-200 dark:border-slate-800 p-6">
        <div className="max-w-6xl mx-auto flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold gradient-text mb-2">⚙️ Ustawienia</h1>
            <p className="text-gray-600 dark:text-gray-400">Zarządzaj swoim profilem i integracjami</p>
          </div>
          <Link
            href="/"
            className="px-4 py-2 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-lg hover:from-purple-600 hover:to-blue-600 transition-all"
          >
            💬 Powrót do Chatu
          </Link>
        </div>
      </div>

      <div className="max-w-6xl mx-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Sidebar Tabs */}
          <div className="lg:col-span-1">
            <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-lg border border-gray-200 dark:border-slate-800 p-2">
              {tabs.map((tab) => {
                const Icon = tab.icon
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as TabType)}
                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all mb-1 ${
                      activeTab === tab.id
                        ? 'bg-gradient-to-r from-purple-500 to-blue-500 text-white'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-800'
                    }`}
                  >
                    <Icon size={20} />
                    <span className="font-medium">{tab.label}</span>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Content Area */}
          <div className="lg:col-span-3">
            <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-lg border border-gray-200 dark:border-slate-800 p-6">
              {/* Profile Tab */}
              {activeTab === 'profile' && (
                <div>
                  <h2 className="text-2xl font-bold mb-6 text-gray-800 dark:text-gray-200">👤 Profil Użytkownika</h2>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                        Imię i Nazwisko
                      </label>
                      <input
                        type="text"
                        value={profile.name}
                        onChange={(e) => setProfile({...profile, name: e.target.value})}
                        className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-purple-500 outline-none"
                        placeholder="Jan Kowalski"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                        Email
                      </label>
                      <input
                        type="email"
                        value={profile.email}
                        onChange={(e) => setProfile({...profile, email: e.target.value})}
                        className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-purple-500 outline-none"
                        placeholder="jan@example.com"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                          Język
                        </label>
                        <select
                          value={profile.language}
                          onChange={(e) => setProfile({...profile, language: e.target.value})}
                          className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-purple-500 outline-none"
                        >
                          <option value="pl">Polski</option>
                          <option value="en">English</option>
                          <option value="de">Deutsch</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                          Strefa Czasowa
                        </label>
                        <select
                          value={profile.timezone}
                          onChange={(e) => setProfile({...profile, timezone: e.target.value})}
                          className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-purple-500 outline-none"
                        >
                          <option value="Europe/Warsaw">Europe/Warsaw (GMT+1)</option>
                          <option value="Europe/London">Europe/London (GMT+0)</option>
                          <option value="America/New_York">America/New_York (GMT-5)</option>
                        </select>
                      </div>
                    </div>
                    <div className="bg-purple-50 dark:bg-purple-900/20 p-4 rounded-xl">
                      <p className="text-sm text-gray-700 dark:text-gray-300">
                        <strong>User ID:</strong> {userId}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Integrations Tab */}
              {activeTab === 'integrations' && (
                <div>
                  <h2 className="text-2xl font-bold mb-6 text-gray-800 dark:text-gray-200">🔗 Integracje</h2>

                  {/* SMTP */}
                  <div className="mb-8">
                    <div className="flex items-center gap-2 mb-4">
                      <Mail className="text-purple-500" />
                      <h3 className="text-xl font-semibold text-gray-800 dark:text-gray-200">SMTP (Email)</h3>
                    </div>
                    <div className="space-y-4 pl-8">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                            SMTP Host
                          </label>
                          <input
                            type="text"
                            value={integrations.smtp_host}
                            onChange={(e) => setIntegrations({...integrations, smtp_host: e.target.value})}
                            className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-800 dark:text-gray-200"
                            placeholder="smtp.gmail.com"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                            Port
                          </label>
                          <input
                            type="text"
                            value={integrations.smtp_port}
                            onChange={(e) => setIntegrations({...integrations, smtp_port: e.target.value})}
                            className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-800 dark:text-gray-200"
                            placeholder="587"
                          />
                        </div>
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                          Username
                        </label>
                        <input
                          type="text"
                          value={integrations.smtp_user}
                          onChange={(e) => setIntegrations({...integrations, smtp_user: e.target.value})}
                          className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-800 dark:text-gray-200"
                          placeholder="your-email@gmail.com"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                          Password / App Password
                        </label>
                        <input
                          type="password"
                          value={integrations.smtp_password}
                          onChange={(e) => setIntegrations({...integrations, smtp_password: e.target.value})}
                          className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-800 dark:text-gray-200"
                          placeholder="••••••••"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Google Calendar */}
                  <div className="mb-8">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2">
                        <Calendar className="text-purple-500" />
                        <h3 className="text-xl font-semibold text-gray-800 dark:text-gray-200">Google Calendar</h3>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={integrations.google_calendar_enabled}
                          onChange={(e) => setIntegrations({...integrations, google_calendar_enabled: e.target.checked})}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-300 dark:peer-focus:ring-purple-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-purple-600"></div>
                      </label>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 pl-8">
                      Włącz, aby automatycznie tworzyć wydarzenia w Google Calendar
                    </p>
                  </div>

                  {/* Notion */}
                  <div className="mb-8">
                    <div className="flex items-center gap-2 mb-4">
                      <FileText className="text-purple-500" />
                      <h3 className="text-xl font-semibold text-gray-800 dark:text-gray-200">Notion</h3>
                    </div>
                    <div className="pl-8">
                      <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                        API Key
                      </label>
                      <input
                        type="password"
                        value={integrations.notion_api_key}
                        onChange={(e) => setIntegrations({...integrations, notion_api_key: e.target.value})}
                        className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-800 dark:text-gray-200"
                        placeholder="secret_••••••••"
                      />
                    </div>
                  </div>

                  {/* Todoist */}
                  <div className="mb-8">
                    <div className="flex items-center gap-2 mb-4">
                      <CheckSquare className="text-purple-500" />
                      <h3 className="text-xl font-semibold text-gray-800 dark:text-gray-200">Todoist</h3>
                    </div>
                    <div className="pl-8">
                      <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                        API Token
                      </label>
                      <input
                        type="password"
                        value={integrations.todoist_api_key}
                        onChange={(e) => setIntegrations({...integrations, todoist_api_key: e.target.value})}
                        className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-800 dark:text-gray-200"
                        placeholder="••••••••"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Preferences Tab */}
              {activeTab === 'preferences' && (
                <div>
                  <h2 className="text-2xl font-bold mb-6 text-gray-800 dark:text-gray-200">🎨 Preferencje Interfejsu</h2>
                  <div className="space-y-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-semibold text-gray-800 dark:text-gray-200">Motyw</h3>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Wybierz preferowany motyw</p>
                      </div>
                      <select
                        value={preferences.theme}
                        onChange={(e) => setPreferences({...preferences, theme: e.target.value})}
                        className="px-4 py-2 rounded-lg border border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-800 dark:text-gray-200"
                      >
                        <option value="auto">Auto (systemowy)</option>
                        <option value="light">Jasny</option>
                        <option value="dark">Ciemny</option>
                      </select>
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-semibold text-gray-800 dark:text-gray-200">Tryb kompaktowy</h3>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Zmniejsz odstępy między elementami</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={preferences.compact_mode}
                          onChange={(e) => setPreferences({...preferences, compact_mode: e.target.checked})}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-300 dark:peer-focus:ring-purple-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-purple-600"></div>
                      </label>
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-semibold text-gray-800 dark:text-gray-200">Pokazuj nazwy agentów</h3>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Wyświetlaj który agent odpowiedział</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={preferences.show_agent_names}
                          onChange={(e) => setPreferences({...preferences, show_agent_names: e.target.checked})}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-300 dark:peer-focus:ring-purple-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-purple-600"></div>
                      </label>
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-semibold text-gray-800 dark:text-gray-200">Animacje</h3>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Włącz animacje i przejścia</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={preferences.animations_enabled}
                          onChange={(e) => setPreferences({...preferences, animations_enabled: e.target.checked})}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-300 dark:peer-focus:ring-purple-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-purple-600"></div>
                      </label>
                    </div>
                  </div>
                </div>
              )}

              {/* Notifications Tab */}
              {activeTab === 'notifications' && (
                <div>
                  <h2 className="text-2xl font-bold mb-6 text-gray-800 dark:text-gray-200">🔔 Powiadomienia</h2>
                  <div className="space-y-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-semibold text-gray-800 dark:text-gray-200">Email notifications</h3>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Otrzymuj powiadomienia na email</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={notifications.email_notifications}
                          onChange={(e) => setNotifications({...notifications, email_notifications: e.target.checked})}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-300 dark:peer-focus:ring-purple-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-purple-600"></div>
                      </label>
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-semibold text-gray-800 dark:text-gray-200">Push notifications</h3>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Powiadomienia w przeglądarce</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={notifications.push_notifications}
                          onChange={(e) => setNotifications({...notifications, push_notifications: e.target.checked})}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-300 dark:peer-focus:ring-purple-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-purple-600"></div>
                      </label>
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-semibold text-gray-800 dark:text-gray-200">Dźwięk</h3>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Odtwarzaj dźwięk przy powiadomieniach</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={notifications.sound_enabled}
                          onChange={(e) => setNotifications({...notifications, sound_enabled: e.target.checked})}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-300 dark:peer-focus:ring-purple-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-purple-600"></div>
                      </label>
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-semibold text-gray-800 dark:text-gray-200">Powiadamiaj o odpowiedziach</h3>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Gdy agent odpowie na twoją wiadomość</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={notifications.notify_on_response}
                          onChange={(e) => setNotifications({...notifications, notify_on_response: e.target.checked})}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-300 dark:peer-focus:ring-purple-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-purple-600"></div>
                      </label>
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-semibold text-gray-800 dark:text-gray-200">Przypomnienia</h3>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Powiadamiaj o zaplanowanych przypomnieniach</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={notifications.notify_on_reminder}
                          onChange={(e) => setNotifications({...notifications, notify_on_reminder: e.target.checked})}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-300 dark:peer-focus:ring-purple-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-purple-600"></div>
                      </label>
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-semibold text-gray-800 dark:text-gray-200">Dzienna podsumowanie</h3>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Codzienne podsumowanie aktywności</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={notifications.daily_summary}
                          onChange={(e) => setNotifications({...notifications, daily_summary: e.target.checked})}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-300 dark:peer-focus:ring-purple-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-purple-600"></div>
                      </label>
                    </div>
                  </div>
                </div>
              )}

              {/* API Keys Tab */}
              {activeTab === 'api-keys' && (
                <div>
                  <h2 className="text-2xl font-bold mb-6 text-gray-800 dark:text-gray-200">🔐 API Keys</h2>
                  <div className="space-y-6">
                    <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 p-4 rounded-xl">
                      <p className="text-sm text-yellow-800 dark:text-yellow-200">
                        ⚠️ <strong>Uwaga:</strong> Nigdy nie udostępniaj swoich kluczy API. Są one wrażliwe i mogą być użyte do nieautoryzowanego dostępu.
                      </p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                        OpenAI API Key
                      </label>
                      <div className="relative">
                        <input
                          type={showApiKey ? 'text' : 'password'}
                          value={apiKeys.openai_key}
                          onChange={(e) => setApiKeys({...apiKeys, openai_key: e.target.value})}
                          className="w-full px-4 py-3 pr-12 rounded-xl border border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-purple-500 outline-none font-mono text-sm"
                          placeholder="sk-••••••••••••••••••••••••••••••••"
                        />
                        <button
                          onClick={() => setShowApiKey(!showApiKey)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                        >
                          {showApiKey ? <EyeOff size={20} /> : <Eye size={20} />}
                        </button>
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                        Używany przez agenty Vision, Speech i inne. Pobierz z <a href="https://platform.openai.com/api-keys" target="_blank" className="text-purple-500 hover:underline">platform.openai.com</a>
                      </p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                        Domyślny Model OpenAI
                      </label>
                      <select
                        value={apiKeys.openai_model}
                        onChange={(e) => setApiKeys({...apiKeys, openai_model: e.target.value})}
                        className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-purple-500 outline-none"
                      >
                        <option value="gpt-4o">GPT-4o (Recommended)</option>
                        <option value="gpt-4o-mini">GPT-4o Mini (Faster & Cheaper)</option>
                        <option value="gpt-4-turbo">GPT-4 Turbo</option>
                        <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                      </select>
                    </div>
                  </div>
                </div>
              )}

              {/* Data Management Tab */}
              {activeTab === 'data' && (
                <div>
                  <h2 className="text-2xl font-bold mb-6 text-gray-800 dark:text-gray-200">🗄️ Zarządzanie Danymi</h2>
                  <div className="space-y-6">
                    {/* Export Data */}
                    <div className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl p-6">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <Download className="text-blue-500" size={24} />
                            <h3 className="text-xl font-semibold text-gray-800 dark:text-gray-200">Eksportuj Dane</h3>
                          </div>
                          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                            Pobierz wszystkie swoje dane w formacie JSON. Obejmuje konwersacje, nastroje, wydatki i więcej.
                          </p>
                          <button
                            onClick={handleExportData}
                            className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-all flex items-center gap-2"
                          >
                            <Download size={18} />
                            Eksportuj Dane
                          </button>
                        </div>
                      </div>
                    </div>

                    {/* Storage Info */}
                    <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-xl p-6">
                      <h3 className="font-semibold text-gray-800 dark:text-gray-200 mb-4">📊 Wykorzystanie Pamięci</h3>
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-700 dark:text-gray-300">Konwersacje</span>
                          <span className="font-semibold text-gray-800 dark:text-gray-200">125 MB</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-700 dark:text-gray-300">Pliki i obrazy</span>
                          <span className="font-semibold text-gray-800 dark:text-gray-200">342 MB</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-700 dark:text-gray-300">Analityka</span>
                          <span className="font-semibold text-gray-800 dark:text-gray-200">28 MB</span>
                        </div>
                        <div className="border-t border-purple-200 dark:border-purple-800 pt-2 mt-2">
                          <div className="flex justify-between font-semibold">
                            <span className="text-gray-800 dark:text-gray-200">Razem</span>
                            <span className="text-purple-600 dark:text-purple-400">495 MB / 5 GB</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Delete Account */}
                    <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <Trash2 className="text-red-500" size={24} />
                            <h3 className="text-xl font-semibold text-gray-800 dark:text-gray-200">Usuń Konto</h3>
                          </div>
                          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                            <strong className="text-red-600 dark:text-red-400">Uwaga:</strong> Ta akcja jest <strong>NIEODWRACALNA</strong>.
                            Wszystkie twoje dane, konwersacje, integracje i ustawienia zostaną trwale usunięte.
                          </p>
                          <button
                            onClick={handleDeleteAccount}
                            className="px-6 py-3 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-all flex items-center gap-2"
                          >
                            <Trash2 size={18} />
                            Usuń Konto
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Save Button */}
              <div className="mt-8 flex justify-end gap-4">
                <button
                  onClick={() => window.location.reload()}
                  className="px-6 py-3 border border-gray-300 dark:border-slate-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-800 transition-all"
                >
                  Anuluj
                </button>
                <button
                  onClick={handleSave}
                  className="px-6 py-3 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-lg hover:from-purple-600 hover:to-blue-600 transition-all flex items-center gap-2"
                >
                  <Save size={18} />
                  Zapisz Zmiany
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
