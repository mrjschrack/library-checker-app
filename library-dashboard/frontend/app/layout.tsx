import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Library Dashboard',
  description: 'Find books from your Goodreads list at your local libraries',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 dark:bg-gray-900">
        {children}
      </body>
    </html>
  )
}
