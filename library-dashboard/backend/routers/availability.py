from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import uuid
import asyncio

from models import (
    get_db, User, Book, Library, AvailabilityCache,
    AvailabilityCheckRequest, AvailabilityResponse, AvailabilityCheckAllResponse
)
from services import check_availability, AvailabilityStatus

router = APIRouter(prefix="/api/availability", tags=["availability"])

# For MVP, use a single default user
DEFAULT_USER_ID = 1

# Cache duration in hours
CACHE_DURATION_HOURS = 4

# Track running jobs
running_jobs = {}


def get_or_create_default_user(db: Session) -> User:
    """Get or create the default user for MVP."""
    user = db.query(User).filter(User.id == DEFAULT_USER_ID).first()
    if not user:
        user = User(id=DEFAULT_USER_ID, email="default@local")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


async def check_book_availability(book: Book, libraries: List[Library], db: Session):
    """Check availability of a single book across all libraries."""
    results = []

    for library in libraries:
        if not library.is_active:
            continue

        # Check cache first
        cache = db.query(AvailabilityCache).filter(
            AvailabilityCache.book_id == book.id,
            AvailabilityCache.library_id == library.id
        ).first()

        # Use cache if fresh
        if cache and cache.expires_at and cache.expires_at > datetime.utcnow():
            results.append(cache)
            continue

        # Perform availability check
        result = await check_availability(
            base_url=library.base_url,
            title=book.title,
            author=book.author
        )

        # Update or create cache entry
        if cache:
            cache.status = result.status.value
            cache.search_url = result.search_url
            cache.libby_url = result.libby_url
            cache.checked_at = datetime.utcnow()
            cache.expires_at = datetime.utcnow() + timedelta(hours=CACHE_DURATION_HOURS)
            if result.status == AvailabilityStatus.ERROR:
                cache.consecutive_failures += 1
            else:
                cache.consecutive_failures = 0
        else:
            cache = AvailabilityCache(
                book_id=book.id,
                library_id=library.id,
                status=result.status.value,
                search_url=result.search_url,
                libby_url=result.libby_url,
                checked_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=CACHE_DURATION_HOURS),
                consecutive_failures=1 if result.status == AvailabilityStatus.ERROR else 0
            )
            db.add(cache)

        db.commit()
        db.refresh(cache)
        results.append(cache)

    return results


async def check_all_books_task(job_id: str, user_id: int):
    """Background task to check availability for all books."""
    from models.database import SessionLocal

    db = SessionLocal()
    try:
        running_jobs[job_id] = {"status": "running", "progress": 0}

        books = db.query(Book).filter(Book.user_id == user_id).all()
        libraries = db.query(Library).filter(
            Library.user_id == user_id,
            Library.is_active == True
        ).all()

        if not books or not libraries:
            running_jobs[job_id] = {"status": "completed", "progress": 100}
            return

        total = len(books)
        for i, book in enumerate(books):
            await check_book_availability(book, libraries, db)
            running_jobs[job_id]["progress"] = int((i + 1) / total * 100)
            # Small delay between books to avoid rate limiting
            await asyncio.sleep(0.5)

        running_jobs[job_id] = {"status": "completed", "progress": 100}

    except Exception as e:
        running_jobs[job_id] = {"status": "error", "error": str(e)}
    finally:
        db.close()


@router.post("/check", response_model=List[AvailabilityResponse])
async def check_single_book(
    request: AvailabilityCheckRequest,
    db: Session = Depends(get_db)
):
    """Check availability for a single book across all libraries."""
    user = get_or_create_default_user(db)

    book = db.query(Book).filter(
        Book.id == request.book_id,
        Book.user_id == user.id
    ).first()

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    libraries = db.query(Library).filter(
        Library.user_id == user.id,
        Library.is_active == True
    ).all()

    if not libraries:
        raise HTTPException(status_code=400, detail="No libraries configured")

    results = await check_book_availability(book, libraries, db)

    return [
        AvailabilityResponse(
            book_id=r.book_id,
            library_id=r.library_id,
            library_name=r.library.name,
            status=r.status,
            search_url=r.search_url,
            libby_url=r.libby_url,
            checked_at=r.checked_at
        )
        for r in results
    ]


@router.post("/check-all", response_model=AvailabilityCheckAllResponse)
async def check_all_books(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start a background job to check availability for all books."""
    user = get_or_create_default_user(db)

    job_id = str(uuid.uuid4())
    background_tasks.add_task(check_all_books_task, job_id, user.id)

    return AvailabilityCheckAllResponse(
        job_id=job_id,
        message="Availability check started"
    )


@router.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a background availability check job."""
    if job_id not in running_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return running_jobs[job_id]


@router.get("/{book_id}", response_model=List[AvailabilityResponse])
async def get_cached_availability(book_id: int, db: Session = Depends(get_db)):
    """Get cached availability for a book."""
    user = get_or_create_default_user(db)

    book = db.query(Book).filter(
        Book.id == book_id,
        Book.user_id == user.id
    ).first()

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    return [
        AvailabilityResponse(
            book_id=cache.book_id,
            library_id=cache.library_id,
            library_name=cache.library.name,
            status=cache.status,
            search_url=cache.search_url,
            libby_url=cache.libby_url,
            checked_at=cache.checked_at
        )
        for cache in book.availability_cache
    ]
