# Library Dashboard

A web app that syncs your Goodreads "to-read" shelf and shows book availability across your local libraries (Libby/OverDrive).

## Features

- **Goodreads Sync**: Paste your RSS feed URL to import your to-read list
- **Multi-Library Support**: Check availability across multiple OverDrive libraries
- **Visual Dashboard**: Color-coded badges show availability at a glance
  - 🟢 Green = Available to borrow now
  - 🟡 Yellow = Available to place hold
  - ⚪ Gray = Not available
  - 🔵 Blue = Status unknown
- **One-Click Actions**: Borrow or place holds directly from the dashboard
- **Mobile-Friendly**: Responsive design works on any device

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone and navigate to project
cd library-dashboard

# Start all services
docker-compose up

# Open http://localhost:3000
```

### Option 2: Manual Setup

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Run the server
python main.py
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Configuration

### 1. Find Your Goodreads RSS URL

1. Go to [goodreads.com](https://goodreads.com) and sign in
2. Click "My Books"
3. Select your "to-read" shelf
4. Look for the RSS icon at the bottom of the page
5. Copy the RSS feed URL

### 2. Add Your Libraries

Common Colorado OverDrive URLs:
- Denver Public Library: `https://denver.overdrive.com`
- Poudre River Library: `https://poudre.overdrive.com`
- Clearview Library: `https://coloradodc.overdrive.com`
- Across Colorado Digital: `https://acdc.overdrive.com`

You'll need your library card number and PIN for each library.

## Tech Stack

- **Frontend**: Next.js 14, React, Tailwind CSS
- **Backend**: Python FastAPI, SQLAlchemy, Playwright
- **Database**: SQLite (dev), PostgreSQL (prod)

## API Documentation

Once running, visit `http://localhost:8000/docs` for the interactive API documentation.

## Development

```bash
# Run backend tests
cd backend
pytest

# Run frontend in dev mode
cd frontend
npm run dev
```

## Deployment

### Vercel (Frontend)
```bash
cd frontend
vercel
```

### Railway (Backend)
The backend includes a Dockerfile ready for Railway deployment.

## Security Notes

- Library credentials are encrypted at rest using Fernet encryption
- Set a strong `ENCRYPTION_KEY` environment variable in production
- Never commit your `.env` file

## Troubleshooting

**"No results found" for books that exist:**
- Try checking manually on the library site
- Some books may have different titles in the library catalog

**Availability check is slow:**
- Each library check requires loading a web page
- Results are cached for 4 hours

**Login fails:**
- Verify your library card number and PIN
- Some libraries may have additional authentication steps

## License

MIT
