'use client'

import { useState, useEffect, useCallback } from 'react'
import Header from '@/components/Header'
import BookGrid from '@/components/BookGrid'
import { BookWithAvailability, getBooks, checkAllAvailability, getJobStatus } from '@/lib/api'

export default function Dashboard() {
  const [books, setBooks] = useState<BookWithAvailability[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isRefreshingAll, setIsRefreshingAll] = useState(false)
  const [refreshProgress, setRefreshProgress] = useState(0)
  const [refreshJobId, setRefreshJobId] = useState<string | null>(null)

  const fetchBooks = useCallback(async () => {
    try {
      const data = await getBooks()
      setBooks(data)
      setError(null)
    } catch (err) {
      console.error('Failed to fetch books:', err)
      setError('Failed to load books. Make sure the backend is running.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchBooks()
  }, [fetchBooks])

  useEffect(() => {
    if (!refreshJobId) return

    let isCancelled = false
    const interval = setInterval(async () => {
      try {
        const status = await getJobStatus(refreshJobId)
        if (isCancelled) return

        if (status.status === 'running') {
          setRefreshProgress(status.progress ?? 0)
          return
        }

        clearInterval(interval)
        setIsRefreshingAll(false)
        setRefreshJobId(null)
        setRefreshProgress(status.progress ?? 100)

        if (status.status === 'completed') {
          await fetchBooks()
        } else {
          setError(status.error || 'Availability refresh failed.')
        }
      } catch (err) {
        clearInterval(interval)
        if (!isCancelled) {
          setIsRefreshingAll(false)
          setRefreshJobId(null)
          setError('Failed to refresh availability.')
        }
      }
    }, 1000)

    return () => {
      isCancelled = true
      clearInterval(interval)
    }
  }, [refreshJobId, fetchBooks])

  const handleBookUpdate = (updatedBook: BookWithAvailability) => {
    setBooks(prev =>
      prev.map(book =>
        book.id === updatedBook.id ? updatedBook : book
      )
    )
  }

  const handleRefreshAll = async () => {
    try {
      setIsRefreshingAll(true)
      setRefreshProgress(0)
      const job = await checkAllAvailability(true)
      setRefreshJobId(job.job_id)
    } catch (err) {
      setIsRefreshingAll(false)
      setError('Failed to start availability refresh.')
    }
  }

  // Count available books
  const availableCount = books.filter(book =>
    book.availability?.some(a => a.status === 'available')
  ).length

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats */}
        {!isLoading && books.length > 0 && (
          <div className="mb-6 flex flex-wrap gap-4 items-center">
            <div className="bg-white dark:bg-gray-800 rounded-lg px-4 py-3 shadow-sm border border-gray-200 dark:border-gray-700">
              <span className="text-2xl font-bold text-gray-900 dark:text-white">
                {books.length}
              </span>
              <span className="text-gray-600 dark:text-gray-400 ml-2">
                books on your list
              </span>
            </div>
            {availableCount > 0 && (
              <div className="bg-green-50 dark:bg-green-900/20 rounded-lg px-4 py-3 shadow-sm border border-green-200 dark:border-green-800">
                <span className="text-2xl font-bold text-green-700 dark:text-green-400">
                  {availableCount}
                </span>
                <span className="text-green-600 dark:text-green-400 ml-2">
                  available now!
                </span>
              </div>
            )}
            <button
              onClick={handleRefreshAll}
              disabled={isRefreshingAll}
              className="ml-auto px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title="Refresh availability for all books"
            >
              {isRefreshingAll ? `Refreshing ${refreshProgress}%` : 'Refresh All'}
            </button>
          </div>
        )}

        {isRefreshingAll && (
          <div className="mb-6">
            <div className="h-2 w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-600 transition-all"
                style={{ width: `${refreshProgress}%` }}
              />
            </div>
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="mb-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <p className="text-red-800 dark:text-red-300">{error}</p>
            <p className="text-red-600 dark:text-red-400 text-sm mt-1">
              Run <code className="bg-red-100 dark:bg-red-900 px-1 rounded">docker-compose up</code> to start the backend.
            </p>
          </div>
        )}

        {/* Book Grid */}
        <BookGrid
          books={books}
          onBookUpdate={handleBookUpdate}
          isLoading={isLoading}
        />
      </main>
    </div>
  )
}
