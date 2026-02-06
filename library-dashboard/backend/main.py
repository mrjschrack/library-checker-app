from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from models import init_db
from routers import goodreads_router, libraries_router, availability_router, checkout_router

# Initialize FastAPI app
app = FastAPI(
    title="Library Dashboard API",
    description="API for syncing Goodreads books and checking library availability",
    version="1.0.0"
)

# Configure CORS - allow all origins for development
# In production, this should be restricted to the actual frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev/testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(goodreads_router)
app.include_router(libraries_router)
app.include_router(availability_router)
app.include_router(checkout_router)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()
    print("Database initialized")


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "status": "ok",
        "message": "Library Dashboard API is running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
