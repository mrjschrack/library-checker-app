'use client'

import { BookWithAvailability } from '@/lib/api'
import BookCard from './BookCard'

interface BookGridProps {
  books: BookWithAvailability[]
  onBookUpdate?: (book: BookWithAvailability) => void
  isLoading?: boolean
}

export default function BookGrid({ books, onBookUpdate, isLoading }: BookGridProps) {
  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[...Array(6)].map((_, i) => (
          <div
            key={i}
            className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden animate-pulse"
          >
            <div className="flex">
              <div className="w-24 sm:w-32 h-40 bg-gray-200 dark:bg-gray-700" />
              <div className="flex-1 p-4 space-y-3">
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
                <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
                <div className="flex gap-2 mt-4">
                  <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded-full w-20" />
                  <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded-full w-20" />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (books.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-400 dark:text-gray-500 mb-4">
          <svg
            className="mx-auto h-12 w-12"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
            />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
          No books yet
        </h3>
        <p className="text-gray-600 dark:text-gray-400 max-w-md mx-auto">
          Add your Goodreads RSS feed URL in settings to see your to-read books here.
        </p>
      </div>
    )
  }

  // Sort books: those with available copies first
  const sortedBooks = [...books].sort((a, b) => {
    const aAvailable = a.availability?.some(av => av.status === 'available') ? 1 : 0
    const bAvailable = b.availability?.some(av => av.status === 'available') ? 1 : 0
    return bAvailable - aAvailable
  })

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {sortedBooks.map((book) => (
        <BookCard
          key={book.id}
          book={book}
          onUpdate={onBookUpdate}
        />
      ))}
    </div>
  )
}
