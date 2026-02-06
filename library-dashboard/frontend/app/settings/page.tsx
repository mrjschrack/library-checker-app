'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { ArrowLeft, Plus, Trash2, Save, Loader2, CheckCircle, XCircle, Rss } from 'lucide-react'
import { Library, getLibraries, addLibrary, deleteLibrary, syncGoodreads } from '@/lib/api'

export default function Settings() {
  const [libraries, setLibraries] = useState<Library[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [goodreadsUrl, setGoodreadsUrl] = useState('')
  const [isSyncing, setIsSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState<{ success: boolean; message: string } | null>(null)

  // New library form
  const [showAddForm, setShowAddForm] = useState(false)
  const [newLibrary, setNewLibrary] = useState({
    name: '',
    base_url: '',
    card_number: '',
    pin: '',
  })
  const [isAdding, setIsAdding] = useState(false)

  useEffect(() => {
    fetchLibraries()
    // Load saved Goodreads URL from localStorage
    const savedUrl = localStorage.getItem('goodreads_rss_url')
    if (savedUrl) setGoodreadsUrl(savedUrl)
  }, [])

  const fetchLibraries = async () => {
    try {
      const data = await getLibraries()
      setLibraries(data)
    } catch (error) {
      console.error('Failed to fetch libraries:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSyncGoodreads = async () => {
    if (!goodreadsUrl.trim()) return

    setIsSyncing(true)
    setSyncResult(null)

    try {
      const books = await syncGoodreads(goodreadsUrl)
      localStorage.setItem('goodreads_rss_url', goodreadsUrl)
      setSyncResult({ success: true, message: `Synced ${books.length} books from Goodreads!` })
    } catch (error) {
      setSyncResult({ success: false, message: 'Failed to sync. Check your RSS URL.' })
    } finally {
      setIsSyncing(false)
    }
  }

  const handleAddLibrary = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsAdding(true)

    try {
      const library = await addLibrary({
        name: newLibrary.name,
        base_url: newLibrary.base_url.replace(/\/$/, ''), // Remove trailing slash
        card_number: newLibrary.card_number,
        is_active: true,
      })
      setLibraries(prev => [...prev, library])
      setNewLibrary({ name: '', base_url: '', card_number: '', pin: '' })
      setShowAddForm(false)
    } catch (error) {
      console.error('Failed to add library:', error)
    } finally {
      setIsAdding(false)
    }
  }

  const handleDeleteLibrary = async (id: number) => {
    if (!confirm('Are you sure you want to remove this library?')) return

    try {
      await deleteLibrary(id)
      setLibraries(prev => prev.filter(lib => lib.id !== id))
    } catch (error) {
      console.error('Failed to delete library:', error)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center h-16">
            <Link
              href="/"
              className="flex items-center gap-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
            >
              <ArrowLeft className="h-5 w-5" />
              <span>Back to Dashboard</span>
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Goodreads Section */}
        <section className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center gap-3 mb-4">
            <Rss className="h-6 w-6 text-orange-500" />
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              Goodreads Sync
            </h2>
          </div>

          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Enter your Goodreads profile URL or user ID to sync your "Want to Read" shelf.
          </p>

          <div className="space-y-4">
            <div>
              <label htmlFor="goodreads-url" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Goodreads Profile URL or User ID
              </label>
              <input
                id="goodreads-url"
                type="text"
                value={goodreadsUrl}
                onChange={(e) => setGoodreadsUrl(e.target.value)}
                placeholder="goodreads.com/user/show/12345678 or just 12345678"
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <button
              onClick={handleSyncGoodreads}
              disabled={isSyncing || !goodreadsUrl.trim()}
              className="flex items-center gap-2 px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isSyncing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Rss className="h-4 w-4" />
              )}
              {isSyncing ? 'Syncing...' : 'Sync Books'}
            </button>

            {syncResult && (
              <div className={`flex items-center gap-2 p-3 rounded-lg ${
                syncResult.success
                  ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300'
                  : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300'
              }`}>
                {syncResult.success ? (
                  <CheckCircle className="h-5 w-5" />
                ) : (
                  <XCircle className="h-5 w-5" />
                )}
                {syncResult.message}
              </div>
            )}
          </div>

          <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
            <h4 className="font-medium text-gray-900 dark:text-white mb-2">How to find your User ID:</h4>

            <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mt-2 mb-1">From the Goodreads App:</p>
            <ol className="text-sm text-gray-600 dark:text-gray-400 space-y-1 list-decimal list-inside">
              <li>Open Goodreads app → tap your profile icon</li>
              <li>Tap the Share button (top right)</li>
              <li>Copy the link and paste it above</li>
            </ol>

            <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mt-3 mb-1">From a Browser:</p>
            <ol className="text-sm text-gray-600 dark:text-gray-400 space-y-1 list-decimal list-inside">
              <li>Go to goodreads.com and sign in</li>
              <li>Tap your profile picture</li>
              <li>Copy the URL (it has your ID number in it)</li>
            </ol>
          </div>
        </section>

        {/* Libraries Section */}
        <section className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              Your Libraries
            </h2>
            <button
              onClick={() => setShowAddForm(true)}
              className="flex items-center gap-2 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Plus className="h-4 w-4" />
              Add Library
            </button>
          </div>

          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Add your library cards to check book availability and enable one-click checkout.
          </p>

          {/* Library List */}
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2].map(i => (
                <div key={i} className="h-20 bg-gray-100 dark:bg-gray-700 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : libraries.length === 0 ? (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              No libraries added yet. Click "Add Library" to get started.
            </div>
          ) : (
            <div className="space-y-3">
              {libraries.map(library => (
                <div
                  key={library.id}
                  className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
                >
                  <div>
                    <h3 className="font-medium text-gray-900 dark:text-white">
                      {library.name}
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {library.base_url}
                    </p>
                  </div>
                  <button
                    onClick={() => handleDeleteLibrary(library.id)}
                    className="p-2 text-red-500 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                  >
                    <Trash2 className="h-5 w-5" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Add Library Form */}
          {showAddForm && (
            <form onSubmit={handleAddLibrary} className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg space-y-4">
              <h3 className="font-medium text-gray-900 dark:text-white">Add New Library</h3>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Library Name
                  </label>
                  <input
                    type="text"
                    required
                    value={newLibrary.name}
                    onChange={(e) => setNewLibrary(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="Denver Public Library"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    OverDrive URL
                  </label>
                  <input
                    type="url"
                    required
                    value={newLibrary.base_url}
                    onChange={(e) => setNewLibrary(prev => ({ ...prev, base_url: e.target.value }))}
                    placeholder="https://denver.overdrive.com"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Library Card Number
                  </label>
                  <input
                    type="text"
                    required
                    value={newLibrary.card_number}
                    onChange={(e) => setNewLibrary(prev => ({ ...prev, card_number: e.target.value }))}
                    placeholder="12345678"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    PIN
                  </label>
                  <input
                    type="password"
                    required
                    value={newLibrary.pin}
                    onChange={(e) => setNewLibrary(prev => ({ ...prev, pin: e.target.value }))}
                    placeholder="****"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  type="submit"
                  disabled={isAdding}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {isAdding ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Save className="h-4 w-4" />
                  )}
                  {isAdding ? 'Adding...' : 'Add Library'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowAddForm(false)}
                  className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}

          {/* Common Libraries */}
          <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
            <h4 className="font-medium text-gray-900 dark:text-white mb-2">Common Colorado Libraries:</h4>
            <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
              <li>• Denver Public Library: <code className="bg-gray-200 dark:bg-gray-600 px-1 rounded">https://denver.overdrive.com</code></li>
              <li>• Poudre River Library: <code className="bg-gray-200 dark:bg-gray-600 px-1 rounded">https://poudre.overdrive.com</code></li>
              <li>• Clearview Library: <code className="bg-gray-200 dark:bg-gray-600 px-1 rounded">https://coloradodc.overdrive.com</code></li>
            </ul>
          </div>
        </section>
      </main>
    </div>
  )
}
