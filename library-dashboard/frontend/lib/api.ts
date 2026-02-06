const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface Book {
  id: number
  goodreads_id: string
  title: string
  author: string
  isbn13?: string
  cover_url?: string
  date_added: string
  shelf: string
}

export interface Library {
  id: number
  name: string
  base_url: string
  card_number?: string
  is_active: boolean
}

export interface Availability {
  book_id: number
  library_id: number
  library_name: string
  status: 'available' | 'hold' | 'unavailable' | 'unknown' | 'not_found' | 'error'
  search_url: string
  libby_url?: string  // share.libbyapp.com link
  checked_at: string
}

export interface BookWithAvailability extends Book {
  availability: Availability[]
}

// Goodreads endpoints
export async function syncGoodreads(rssUrl: string): Promise<Book[]> {
  const res = await fetch(`${API_BASE}/api/goodreads/sync`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rss_url: rssUrl }),
  })
  if (!res.ok) throw new Error('Failed to sync Goodreads')
  return res.json()
}

export async function getBooks(): Promise<BookWithAvailability[]> {
  const res = await fetch(`${API_BASE}/api/goodreads/books`)
  if (!res.ok) throw new Error('Failed to fetch books')
  return res.json()
}

// Library endpoints
export async function getLibraries(): Promise<Library[]> {
  const res = await fetch(`${API_BASE}/api/libraries`)
  if (!res.ok) throw new Error('Failed to fetch libraries')
  return res.json()
}

export async function addLibrary(library: Omit<Library, 'id'>): Promise<Library> {
  const res = await fetch(`${API_BASE}/api/libraries`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(library),
  })
  if (!res.ok) throw new Error('Failed to add library')
  return res.json()
}

export async function updateLibrary(id: number, library: Partial<Library>): Promise<Library> {
  const res = await fetch(`${API_BASE}/api/libraries/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(library),
  })
  if (!res.ok) throw new Error('Failed to update library')
  return res.json()
}

export async function deleteLibrary(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/api/libraries/${id}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error('Failed to delete library')
}

// Availability endpoints
export async function checkAvailability(bookId: number, force = false): Promise<Availability[]> {
  const res = await fetch(`${API_BASE}/api/availability/check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ book_id: bookId, force }),
  })
  if (!res.ok) throw new Error('Failed to check availability')
  return res.json()
}

export async function checkAllAvailability(force = false): Promise<{ job_id: string }> {
  const url = `${API_BASE}/api/availability/check-all${force ? '?force=true' : ''}`
  const res = await fetch(url, {
    method: 'POST',
  })
  if (!res.ok) throw new Error('Failed to start availability check')
  return res.json()
}

export interface JobStatus {
  status: 'running' | 'completed' | 'error'
  progress: number
  error?: string
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API_BASE}/api/availability/job/${jobId}`)
  if (!res.ok) throw new Error('Failed to get job status')
  return res.json()
}

// Checkout endpoints
export async function borrowBook(bookId: number, libraryId: number): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${API_BASE}/api/checkout/borrow`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ book_id: bookId, library_id: libraryId }),
  })
  if (!res.ok) throw new Error('Failed to borrow book')
  return res.json()
}

export async function placeHold(bookId: number, libraryId: number): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${API_BASE}/api/checkout/hold`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ book_id: bookId, library_id: libraryId }),
  })
  if (!res.ok) throw new Error('Failed to place hold')
  return res.json()
}

export function getLibbyDeepLink(searchUrl: string): string {
  // Convert OverDrive URL to Libby deep link
  // Example: https://denver.overdrive.com/search?query=... -> libbyapp://open/...
  const url = new URL(searchUrl)
  const query = url.searchParams.get('query') || ''
  return `https://libbyapp.com/search/query-${encodeURIComponent(query)}`
}
