from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout
from dataclasses import dataclass
from typing import Optional
from enum import Enum
import asyncio
import re


class AvailabilityStatus(str, Enum):
    AVAILABLE = "available"
    HOLD = "hold"
    UNAVAILABLE = "unavailable"
    NOT_FOUND = "not_found"
    UNKNOWN = "unknown"
    ERROR = "error"


@dataclass
class AvailabilityResult:
    status: AvailabilityStatus
    search_url: str
    libby_url: Optional[str] = None  # share.libbyapp.com link
    wait_time: Optional[str] = None  # e.g., "2 weeks"
    copies_available: Optional[int] = None
    message: Optional[str] = None


def build_search_url(base_url: str, title: str, author: Optional[str] = None) -> str:
    """Build OverDrive search URL from book info."""
    # Clean and encode search query
    query_parts = [title]
    if author:
        query_parts.append(author)

    query = ' '.join(query_parts)
    # Remove special characters that might break search
    query = re.sub(r'[^\w\s]', ' ', query)
    query = re.sub(r'\s+', ' ', query).strip()
    encoded_query = query.replace(' ', '+')

    return f"{base_url.rstrip('/')}/search?query={encoded_query}"


async def check_availability(
    base_url: str,
    title: str,
    author: Optional[str] = None,
    timeout: int = 30000
) -> AvailabilityResult:
    """
    Check book availability on an OverDrive library site.

    Uses Playwright to navigate and detect availability status.
    """
    search_url = build_search_url(base_url, title, author)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            page = await context.new_page()

            try:
                await page.goto(search_url, timeout=timeout, wait_until='domcontentloaded')

                # Wait for content to load
                await page.wait_for_timeout(2000)

                # Try to get the OverDrive media ID for Libby deep link
                media_id = await _extract_media_id(page)
                libby_url = f"https://share.libbyapp.com/title/{media_id}" if media_id else None

                result = await _detect_availability(page, search_url, libby_url)
                return result

            finally:
                await browser.close()

    except PlaywrightTimeout:
        return AvailabilityResult(
            status=AvailabilityStatus.ERROR,
            search_url=search_url,
            message="Page load timeout"
        )
    except Exception as e:
        return AvailabilityResult(
            status=AvailabilityStatus.ERROR,
            search_url=search_url,
            message=str(e)
        )


async def _extract_media_id(page: Page) -> Optional[str]:
    """Extract the OverDrive media ID from search results."""
    try:
        # Look for data-media-id attribute on borrow/hold buttons or title cards
        element = await page.locator('[data-media-id]').first.get_attribute('data-media-id')
        if element:
            return element
    except Exception:
        pass

    # Try to get from href links
    try:
        href = await page.locator('a[href*="/media/"]').first.get_attribute('href')
        if href:
            match = re.search(r'/media/(\d+)', href)
            if match:
                return match.group(1)
    except Exception:
        pass

    return None


async def _detect_availability(page: Page, search_url: str, libby_url: Optional[str] = None) -> AvailabilityResult:
    """
    Detect availability status from page content.

    Uses multiple detection layers for robustness.
    """
    # Layer 1: Check for borrow/hold buttons FIRST (most reliable)
    # This catches cases where "0 results" text exists in hidden elements
    available_selectors = [
        '.is-borrow',           # OverDrive borrow button class
        '.js-borrow',           # OverDrive borrow button class
        'a[aria-label*="Borrow"]',  # Borrow links
        '.TitleCard-badge--available',
        '[data-availability="available"]',
        '.badge-available',
        '.availability-badge.available',
        'button:has-text("Borrow")',
        'a:has-text("Borrow")',
    ]

    for selector in available_selectors:
        try:
            count = await page.locator(selector).count()
            if count > 0:
                return AvailabilityResult(
                    status=AvailabilityStatus.AVAILABLE,
                    search_url=search_url,
                    libby_url=libby_url,
                    message="Available to borrow"
                )
        except Exception:
            continue

    # Layer 2: Check for hold/waitlist indicators
    hold_selectors = [
        '.is-hold',             # OverDrive hold button class
        '.js-hold',             # OverDrive hold button class
        'a[aria-label*="Place a hold"]',  # Hold links
        '.TitleCard-badge--waitlist',
        '[data-availability="waitlist"]',
        'button:has-text("Place a Hold")',
        'button:has-text("Join Waitlist")',
        'a:has-text("Place a hold")',
    ]

    for selector in hold_selectors:
        try:
            count = await page.locator(selector).count()
            if count > 0:
                # Try to extract wait time
                wait_time = await _extract_wait_time(page)
                return AvailabilityResult(
                    status=AvailabilityStatus.HOLD,
                    search_url=search_url,
                    libby_url=libby_url,
                    wait_time=wait_time,
                    message="Available to place hold"
                )
        except Exception:
            continue

    # Layer 3: Text-based detection (fallback)
    page_content = await page.content()
    page_text = page_content.lower()

    availability_keywords = {
        AvailabilityStatus.AVAILABLE: [
            'borrow now',
            'available to borrow',
            'check out',
            'copies available',
        ],
        AvailabilityStatus.HOLD: [
            'place a hold',
            'join waitlist',
            'people waiting',
            'wait list',
            'no copies available',
        ],
    }

    for status, keywords in availability_keywords.items():
        for keyword in keywords:
            if keyword in page_text:
                return AvailabilityResult(
                    status=status,
                    search_url=search_url,
                    libby_url=libby_url,
                    message=f"Detected via keyword: {keyword}"
                )

    # Layer 4: Check if we found any title cards at all
    title_cards = await page.locator('.TitleCard, .title-card, [class*="TitleCard"]').count()
    if title_cards > 0:
        # Found results but couldn't determine availability
        return AvailabilityResult(
            status=AvailabilityStatus.UNKNOWN,
            search_url=search_url,
            libby_url=libby_url,
            message="Found results but couldn't determine availability"
        )

    # Layer 5: Check for no results (only if no title cards found)
    no_results_indicators = [
        "no results found",
        "didn't match any titles",
        "no titles found",
        "we couldn't find"
    ]
    for indicator in no_results_indicators:
        if indicator in page_text:
            return AvailabilityResult(
                status=AvailabilityStatus.NOT_FOUND,
                search_url=search_url,
                message="No results found"
            )

    # No results found
    return AvailabilityResult(
        status=AvailabilityStatus.NOT_FOUND,
        search_url=search_url,
        message="No matching titles found"
    )


async def _extract_wait_time(page: Page) -> Optional[str]:
    """Try to extract estimated wait time from page."""
    try:
        # Common patterns for wait time
        wait_selectors = [
            '.waitlist-info',
            '[class*="wait"]',
            '.hold-info',
        ]

        for selector in wait_selectors:
            elements = await page.locator(selector).all()
            for element in elements:
                text = await element.text_content()
                if text and 'week' in text.lower():
                    # Extract time info
                    match = re.search(r'(\d+)\s*week', text.lower())
                    if match:
                        return f"{match.group(1)} weeks"
        return None
    except Exception:
        return None


async def perform_checkout(
    page: Page,
    action: str = "borrow"
) -> tuple[bool, str]:
    """
    Attempt to perform a checkout action (borrow or hold).

    Returns (success, message) tuple.
    """
    try:
        if action == "borrow":
            button = page.locator('button:has-text("Borrow"), button:has-text("Check Out")').first
        else:
            button = page.locator('button:has-text("Place a Hold"), button:has-text("Join Waitlist")').first

        if await button.count() == 0:
            return False, f"Could not find {action} button"

        await button.click()
        await page.wait_for_timeout(3000)

        # Check for success indicators
        success_indicators = ['borrowed', 'checked out', 'hold placed', 'added to holds']
        page_text = (await page.content()).lower()

        for indicator in success_indicators:
            if indicator in page_text:
                return True, f"Successfully {action}ed"

        return False, "Action completed but couldn't confirm success"

    except Exception as e:
        return False, str(e)


async def login_to_library(
    page: Page,
    card_number: str,
    pin: str
) -> tuple[bool, str]:
    """
    Attempt to log in to library.

    Returns (success, message) tuple.
    """
    try:
        # Look for sign-in button
        signin_button = page.locator('button:has-text("Sign In"), .signin-button, [class*="signin"]').first
        if await signin_button.count() > 0:
            await signin_button.click()
            await page.wait_for_timeout(2000)

        # Fill credentials
        username_field = page.locator('#username, input[name="username"], input[type="text"]').first
        password_field = page.locator('#password, input[name="password"], input[type="password"]').first

        if await username_field.count() == 0 or await password_field.count() == 0:
            return False, "Could not find login fields"

        await username_field.fill(card_number)
        await password_field.fill(pin)

        # Submit
        submit_button = page.locator('button[type="submit"], button:has-text("Sign In")').first
        await submit_button.click()

        await page.wait_for_timeout(3000)

        # Check if login succeeded (look for account menu or similar)
        logged_in_indicators = ['my account', 'sign out', 'log out', 'my loans']
        page_text = (await page.content()).lower()

        for indicator in logged_in_indicators:
            if indicator in page_text:
                return True, "Login successful"

        # Check for error messages
        if 'invalid' in page_text or 'incorrect' in page_text:
            return False, "Invalid credentials"

        return False, "Login status unclear"

    except Exception as e:
        return False, str(e)
