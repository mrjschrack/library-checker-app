from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from playwright.async_api import async_playwright

from models import get_db, User, Book, Library, AvailabilityCache, CheckoutRequest, CheckoutResponse
from services import login_to_library, perform_checkout, build_search_url
from utils import decrypt_value

router = APIRouter(prefix="/api/checkout", tags=["checkout"])

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


@router.post("/borrow", response_model=CheckoutResponse)
async def borrow_book(request: CheckoutRequest, db: Session = Depends(get_db)):
    """
    Attempt to borrow a book from a library.

    This will log in to the library and try to borrow the book automatically.
    """
    user = get_or_create_default_user(db)

    book = db.query(Book).filter(
        Book.id == request.book_id,
        Book.user_id == user.id
    ).first()

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    library = db.query(Library).filter(
        Library.id == request.library_id,
        Library.user_id == user.id
    ).first()

    if not library:
        raise HTTPException(status_code=404, detail="Library not found")

    if not library.card_number or not library.pin:
        return CheckoutResponse(
            success=False,
            message="Library credentials not configured",
            action_taken=None
        )

    # Decrypt credentials
    card_number = decrypt_value(library.card_number)
    pin = decrypt_value(library.pin)

    # Build search URL
    search_url = build_search_url(library.base_url, book.title, book.author)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720}
            )
            page = await context.new_page()

            try:
                # Navigate to search page
                await page.goto(search_url, timeout=30000)
                await page.wait_for_timeout(2000)

                # Try to log in
                login_success, login_message = await login_to_library(page, card_number, pin)

                if not login_success:
                    return CheckoutResponse(
                        success=False,
                        message=f"Login failed: {login_message}",
                        action_taken="login_attempt"
                    )

                # Try to borrow
                borrow_success, borrow_message = await perform_checkout(page, "borrow")

                if borrow_success:
                    # Update availability cache
                    cache = db.query(AvailabilityCache).filter(
                        AvailabilityCache.book_id == book.id,
                        AvailabilityCache.library_id == library.id
                    ).first()

                    if cache:
                        cache.status = "borrowed"
                        db.commit()

                return CheckoutResponse(
                    success=borrow_success,
                    message=borrow_message,
                    action_taken="borrow"
                )

            finally:
                await browser.close()

    except Exception as e:
        return CheckoutResponse(
            success=False,
            message=f"Error: {str(e)}",
            action_taken="error"
        )


@router.post("/hold", response_model=CheckoutResponse)
async def place_hold(request: CheckoutRequest, db: Session = Depends(get_db)):
    """
    Attempt to place a hold on a book.

    This will log in to the library and try to place a hold automatically.
    """
    user = get_or_create_default_user(db)

    book = db.query(Book).filter(
        Book.id == request.book_id,
        Book.user_id == user.id
    ).first()

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    library = db.query(Library).filter(
        Library.id == request.library_id,
        Library.user_id == user.id
    ).first()

    if not library:
        raise HTTPException(status_code=404, detail="Library not found")

    if not library.card_number or not library.pin:
        return CheckoutResponse(
            success=False,
            message="Library credentials not configured",
            action_taken=None
        )

    # Decrypt credentials
    card_number = decrypt_value(library.card_number)
    pin = decrypt_value(library.pin)

    # Build search URL
    search_url = build_search_url(library.base_url, book.title, book.author)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720}
            )
            page = await context.new_page()

            try:
                # Navigate to search page
                await page.goto(search_url, timeout=30000)
                await page.wait_for_timeout(2000)

                # Try to log in
                login_success, login_message = await login_to_library(page, card_number, pin)

                if not login_success:
                    return CheckoutResponse(
                        success=False,
                        message=f"Login failed: {login_message}",
                        action_taken="login_attempt"
                    )

                # Try to place hold
                hold_success, hold_message = await perform_checkout(page, "hold")

                if hold_success:
                    # Update availability cache
                    cache = db.query(AvailabilityCache).filter(
                        AvailabilityCache.book_id == book.id,
                        AvailabilityCache.library_id == library.id
                    ).first()

                    if cache:
                        cache.status = "hold_placed"
                        db.commit()

                return CheckoutResponse(
                    success=hold_success,
                    message=hold_message,
                    action_taken="hold"
                )

            finally:
                await browser.close()

    except Exception as e:
        return CheckoutResponse(
            success=False,
            message=f"Error: {str(e)}",
            action_taken="error"
        )


@router.get("/deep-link")
async def get_deep_link(search_url: str):
    """
    Generate a Libby deep link for a search URL.

    Falls back to this when automated checkout fails.
    """
    # Convert OverDrive search URL to Libby-friendly format
    # Libby can open URLs that point to their app
    libby_url = search_url.replace('overdrive.com', 'libbyapp.com')

    return {
        "deep_link": libby_url,
        "web_url": search_url
    }
