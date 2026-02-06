'use client'

import { clsx } from 'clsx'
import { Check, Clock, X, HelpCircle, AlertCircle, Loader2 } from 'lucide-react'
import { Availability } from '@/lib/api'

interface LibraryBadgeProps {
  availability: Availability
  onClick?: () => void
  isLoading?: boolean
}

const statusConfig = {
  available: {
    bg: 'bg-green-100 dark:bg-green-900/30',
    text: 'text-green-800 dark:text-green-300',
    border: 'border-green-300 dark:border-green-700',
    icon: Check,
    label: 'Borrow',
  },
  hold: {
    bg: 'bg-yellow-100 dark:bg-yellow-900/30',
    text: 'text-yellow-800 dark:text-yellow-300',
    border: 'border-yellow-300 dark:border-yellow-700',
    icon: Clock,
    label: 'Hold',
  },
  unavailable: {
    bg: 'bg-gray-100 dark:bg-gray-700',
    text: 'text-gray-600 dark:text-gray-400',
    border: 'border-gray-300 dark:border-gray-600',
    icon: X,
    label: 'Unavailable',
  },
  not_found: {
    bg: 'bg-gray-100 dark:bg-gray-700',
    text: 'text-gray-500 dark:text-gray-500',
    border: 'border-gray-200 dark:border-gray-600',
    icon: X,
    label: 'Not Found',
  },
  unknown: {
    bg: 'bg-blue-100 dark:bg-blue-900/30',
    text: 'text-blue-800 dark:text-blue-300',
    border: 'border-blue-300 dark:border-blue-700',
    icon: HelpCircle,
    label: 'Check',
  },
  error: {
    bg: 'bg-red-100 dark:bg-red-900/30',
    text: 'text-red-800 dark:text-red-300',
    border: 'border-red-300 dark:border-red-700',
    icon: AlertCircle,
    label: 'Error',
  },
}

export default function LibraryBadge({ availability, onClick, isLoading }: LibraryBadgeProps) {
  const config = statusConfig[availability.status] || statusConfig.unknown
  const Icon = isLoading ? Loader2 : config.icon

  return (
    <button
      onClick={onClick}
      disabled={isLoading}
      className={clsx(
        'flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-all',
        config.bg,
        config.text,
        config.border,
        'hover:shadow-md hover:scale-105',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        availability.status === 'available' && 'badge-available'
      )}
      title={`${availability.library_name}: ${config.label}`}
    >
      <Icon className={clsx('h-3 w-3', isLoading && 'animate-spin')} />
      <span className="max-w-[80px] truncate">{availability.library_name}</span>
    </button>
  )
}
