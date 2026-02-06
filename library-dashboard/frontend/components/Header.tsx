'use client'

import { Settings, BookOpen } from 'lucide-react'
import Link from 'next/link'

export default function Header() {
  return (
    <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <Link href="/" className="flex items-center gap-2">
            <BookOpen className="h-8 w-8 text-blue-600" />
            <span className="text-xl font-semibold text-gray-900 dark:text-white">
              Library Dashboard
            </span>
          </Link>

          <div className="flex items-center gap-4">

            <Link
              href="/settings"
              className="p-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              <Settings className="h-6 w-6" />
            </Link>
          </div>
        </div>
      </div>
    </header>
  )
}
