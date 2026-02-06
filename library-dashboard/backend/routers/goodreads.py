from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import logging
from datetime import datetime

from models import (
    get_db, User, Book,
    GoodreadsSyncRequest, BookResponse, BookWithAvailability, AvailabilityResponse
)
from services import fetch_goodreads_rss, validate_rss_url, normalize_goodreads_input

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/goodreads", tags=["goodreads"])

# For MVP, use a single default user
DEFAULT_USER_ID = 1


def get_or_create_default_user(db: Session) -> User:
    """Get or create the default user for MVP."""
    user = db.query(User).filter(User.id == DEFAULT_USER_ID).first()
    if not user:
        user = User(id=DEFAULT_USER_ID, email="default@local")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@router.post("/sync", response_model=List[BookResponse])
async def sync_goodreads(request: GoodreadsSyncRequest, db: Session = Depends(get_db)):
    """
    Sync books from Goodreads RSS feed.

    Fetches the RSS feed, parses books, and stores them in the database.
    """
    # Normalize input (profile URL, user ID, or RSS URL)
    rss_url = normalize_goodreads_input(request.rss_url)
    logger.info(f"Syncing Goodreads - Input: '{request.rss_url}' -> RSS URL: '{rss_url}'")

    try:
        # Fetch books from RSS
        parsed_books = await fetch_goodreads_rss(rss_url)
        logger.info(f"Fetched {len(parsed_books)} books from RSS feed")
    except Exception as e:
        logger.error(f"Failed to fetch RSS feed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch RSS feed: {str(e)}")

    # Get or create default user
    user = get_or_create_default_user(db)

    # Update user's RSS URL
    user.goodreads_rss_url = request.rss_url

    # Load existing books and index by goodreads_id or title+author
    existing_books = db.query(Book).filter(Book.user_id == user.id).all()
    by_goodreads_id = {b.goodreads_id: b for b in existing_books if b.goodreads_id}
    by_title_author = {
        f"{(b.title or '').strip().lower()}::{(b.author or '').strip().lower()}": b
        for b in existing_books if not b.goodreads_id
    }

    synced_books = []
    seen_book_ids = set()

    for parsed in parsed_books:
        key = f"{(parsed.title or '').strip().lower()}::{(parsed.author or '').strip().lower()}"
        book = None

        if parsed.goodreads_id:
            book = by_goodreads_id.get(parsed.goodreads_id)
        if not book:
            book = by_title_author.get(key)

        if book:
            # Update existing book
            book.goodreads_id = parsed.goodreads_id or book.goodreads_id
            book.title = parsed.title
            book.author = parsed.author
            book.isbn13 = parsed.isbn13
            book.cover_url = parsed.cover_url
            book.date_added = parsed.date_added
            book.shelf = parsed.shelf
            synced_books.append(book)
            seen_book_ids.add(book.id)
        else:
            # Create new book
            new_book = Book(
                user_id=user.id,
                goodreads_id=parsed.goodreads_id,
                title=parsed.title,
                author=parsed.author,
                isbn13=parsed.isbn13,
                cover_url=parsed.cover_url,
                date_added=parsed.date_added,
                shelf=parsed.shelf
            )
            db.add(new_book)
            synced_books.append(new_book)

    db.commit()

    # Refresh to get IDs for new books and mark them seen
    for book in synced_books:
        db.refresh(book)
        seen_book_ids.add(book.id)

    # Remove books no longer in the feed
    for book in existing_books:
        if book.id not in seen_book_ids:
            db.delete(book)

    db.commit()

    return synced_books


@router.get("/books", response_model=List[BookWithAvailability])
async def get_books(db: Session = Depends(get_db)):
    """
    Get all synced books with their availability status.
    """
    user = get_or_create_default_user(db)

    books = db.query(Book).filter(Book.user_id == user.id).all()

    result = []
    for book in books:
        # Get most recent availability per library
        latest_by_library = {}
        for cache in sorted(book.availability_cache, key=lambda c: c.checked_at or datetime.min, reverse=True):
            if cache.library_id not in latest_by_library:
                latest_by_library[cache.library_id] = cache

        availability = [
            AvailabilityResponse(
                book_id=cache.book_id,
                library_id=cache.library_id,
                library_name=cache.library.name,
                status=cache.status,
                search_url=cache.search_url,
                libby_url=cache.libby_url,
                checked_at=cache.checked_at
            )
            for cache in latest_by_library.values()
        ]

        result.append(BookWithAvailability(
            id=book.id,
            goodreads_id=book.goodreads_id,
            title=book.title,
            author=book.author,
            isbn13=book.isbn13,
            cover_url=book.cover_url,
            date_added=book.date_added,
            shelf=book.shelf,
            availability=availability
        ))

    return result
