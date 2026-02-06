'use client'

import { useState } from 'react'
import Image from 'next/image'
import { RefreshCw, ExternalLink } from 'lucide-react'
import { BookWithAvailability, checkAvailability, getLibbyDeepLink } from '@/lib/api'
import LibraryBadge from './LibraryBadge'

interface BookCardProps {
  book: BookWithAvailability
  onUpdate?: (book: BookWithAvailability) => void
}

export default function BookCard({ book, onUpdate }: BookCardProps) {
  const [isChecking, setIsChecking] = useState(false)
  const [loadingLibrary, setLoadingLibrary] = useState<number | null>(null)

  const handleRefresh = async () => {
    setIsChecking(true)
    try {
      const availability = await checkAvailability(book.id, true)
      if (onUpdate) {
        onUpdate({ ...book, availability })
      }
    } catch (error) {
      console.error('Failed to check availability:', error)
    } finally {
      setIsChecking(false)
    }
  }

  const handleBadgeClick = async (libraryId: number, status: string, searchUrl: string, libbyUrl?: string) => {
    // Prefer the Libby share URL if available, otherwise fall back to OverDrive search
    const url = libbyUrl || (searchUrl ? getLibbyDeepLink(searchUrl) : '')
    if (!url) return
    window.open(url, '_blank')
  }

  // Sort availability: available first, then hold, then others
  const sortedAvailability = [...(book.availability || [])].sort((a, b) => {
    const order = { available: 0, hold: 1, unknown: 2, unavailable: 3, not_found: 4, error: 5 }
    return (order[a.status] ?? 99) - (order[b.status] ?? 99)
  })

  const hasAvailable = sortedAvailability.some(a => a.status === 'available')

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-xl shadow-sm border overflow-hidden transition-all hover:shadow-lg ${hasAvailable ? 'border-green-300 dark:border-green-700 ring-2 ring-green-100 dark:ring-green-900/30' : 'border-gray-200 dark:border-gray-700'}`}>
      <div className="flex">
        {/* Book Cover */}
        <div className="relative w-24 sm:w-32 flex-shrink-0">
          {book.cover_url ? (
            <Image
              src={book.cover_url}
              alt={book.title}
              fill
              className="object-cover"
              sizes="(max-width: 640px) 96px, 128px"
            />
          ) : (
            <div className="absolute inset-0 bg-gradient-to-br from-gray-200 to-gray-300 dark:from-gray-700 dark:to-gray-600 flex items-center justify-center">
              <span className="text-gray-500 dark:text-gray-400 text-xs text-center px-2">
                No Cover
              </span>
            </div>
          )}
        </div>

        {/* Book Info */}
        <div className="flex-1 p-3 sm:p-4 flex flex-col min-w-0">
          <div className="flex-1">
            <h3 className="font-semibold text-gray-900 dark:text-white text-sm sm:text-base line-clamp-2 mb-1">
              {book.title}
            </h3>
            <p className="text-gray-600 dark:text-gray-400 text-xs sm:text-sm truncate">
              {book.author}
            </p>
          </div>

          {/* Availability Badges */}
          <div className="mt-3 flex flex-wrap gap-1.5">
            {sortedAvailability.length > 0 ? (
              sortedAvailability.map((avail) => (
                <LibraryBadge
                  key={avail.library_id}
                  availability={avail}
                  onClick={() => handleBadgeClick(avail.library_id, avail.status, avail.search_url, avail.libby_url)}
                  isLoading={loadingLibrary === avail.library_id}
                />
              ))
            ) : (
              <span className="text-gray-400 dark:text-gray-500 text-xs italic">
                No libraries configured
              </span>
            )}
          </div>

          {/* Actions */}
          <div className="mt-2 flex items-center gap-2">
            <button
              onClick={handleRefresh}
              disabled={isChecking}
              className="text-gray-500 hover:text-blue-600 dark:text-gray-400 dark:hover:text-blue-400 disabled:opacity-50"
              title="Refresh availability"
            >
              <RefreshCw className={`h-4 w-4 ${isChecking ? 'animate-spin' : ''}`} />
            </button>
            <a
              href={`https://www.goodreads.com/book/show/${book.goodreads_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-500 hover:text-blue-600 dark:text-gray-400 dark:hover:text-blue-400"
              title="View on Goodreads"
            >
              <ExternalLink className="h-4 w-4" />
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}
