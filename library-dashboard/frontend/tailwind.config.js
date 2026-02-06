/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        available: '#22c55e',
        hold: '#eab308',
        unavailable: '#6b7280',
        unknown: '#3b82f6',
        error: '#ef4444',
      },
    },
  },
  plugins: [],
}
