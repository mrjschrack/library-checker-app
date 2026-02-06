#!/bin/bash

# Library Dashboard Development Startup Script
# This script starts both frontend and backend for local development

set -e

echo "🚀 Starting Library Dashboard..."

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: Run this script from the library-dashboard directory"
    exit 1
fi

# Check for Docker
if command -v docker-compose &> /dev/null; then
    echo "📦 Docker found. Starting with Docker Compose..."
    docker-compose up --build
else
    echo "🔧 Docker not found. Starting services manually..."

    # Start backend
    echo "Starting backend..."
    cd backend
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    source venv/bin/activate
    pip install -r requirements.txt -q
    playwright install chromium 2>/dev/null || true

    # Run backend in background
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
    BACKEND_PID=$!
    cd ..

    # Start frontend
    echo "Starting frontend..."
    cd frontend
    npm install -q
    npm run dev &
    FRONTEND_PID=$!
    cd ..

    echo ""
    echo "✅ Services started!"
    echo "   Frontend: http://localhost:3000"
    echo "   Backend:  http://localhost:8000"
    echo "   API Docs: http://localhost:8000/docs"
    echo ""
    echo "Press Ctrl+C to stop all services"

    # Handle cleanup on exit
    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT

    # Wait for processes
    wait
fi
