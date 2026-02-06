import feedparser
import httpx
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass
import re


@dataclass
class GoodreadsBook:
    """Parsed book from Goodreads RSS feed."""
    goodreads_id: str
    title: str
    author: Optional[str]
    isbn13: Optional[str]
    cover_url: Optional[str]
    date_added: Optional[datetime]
    shelf: str


def clean_title(title: str) -> str:
    """Clean up book title - remove rating prefix if present."""
    # Goodreads RSS sometimes includes "★★★★☆ " rating prefix
    cleaned = re.sub(r'^[★☆]+\s*', '', title)
    return cleaned.strip()


def extract_isbn(description: str) -> Optional[str]:
    """Extract ISBN13 from description if present."""
    # Look for ISBN-13 pattern
    match = re.search(r'isbn13:\s*(\d{13})', description, re.IGNORECASE)
    if match:
        return match.group(1)
    # Also try without label
    match = re.search(r'\b(97[89]\d{10})\b', description)
    if match:
        return match.group(1)
    return None


def extract_author_from_title(title_with_author: str) -> tuple[str, Optional[str]]:
    """
    Extract author from title if format is 'Title by Author'.
    Returns (title, author) tuple.
    """
    # Pattern: "Book Title by Author Name"
    match = re.match(r'^(.+?)\s+by\s+(.+)$', title_with_author, re.IGNORECASE)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return title_with_author, None


def parse_goodreads_date(date_str: str) -> Optional[datetime]:
    """Parse date from Goodreads RSS format."""
    if not date_str:
        return None
    try:
        # Common formats from Goodreads
        for fmt in [
            '%a, %d %b %Y %H:%M:%S %z',
            '%a, %d %b %Y %H:%M:%S %Z',
            '%Y-%m-%dT%H:%M:%S%z',
        ]:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None
    except Exception:
        return None


async def fetch_goodreads_rss(rss_url: str) -> List[GoodreadsBook]:
    """
    Fetch and parse Goodreads RSS feed.

    Args:
        rss_url: Full Goodreads RSS URL with key

    Returns:
        List of parsed books
    """
    books = []

    # Fetch RSS feed
    async with httpx.AsyncClient() as client:
        response = await client.get(rss_url, follow_redirects=True, timeout=30)
        response.raise_for_status()
        content = response.text

    # Parse feed
    feed = feedparser.parse(content)

    for entry in feed.entries:
        # Extract book ID from link
        # Format: https://www.goodreads.com/review/show/1234567890
        goodreads_id = None
        if 'link' in entry:
            match = re.search(r'/show/(\d+)', entry.link)
            if match:
                goodreads_id = match.group(1)

        # Extract book_id from guid if available
        if not goodreads_id and 'id' in entry:
            match = re.search(r'(\d+)', entry.id)
            if match:
                goodreads_id = match.group(1)

        # Get title - may include author
        raw_title = entry.get('title', 'Unknown Title')
        title = clean_title(raw_title)

        # Try to get author from dedicated field first
        author = entry.get('author_name')

        # If no author field, try to extract from title
        if not author:
            title, author = extract_author_from_title(title)

        # Get cover image
        cover_url = None
        if 'book_image_url' in entry:
            cover_url = entry.book_image_url
        elif 'media_content' in entry and entry.media_content:
            cover_url = entry.media_content[0].get('url')

        # Get shelf
        shelf = entry.get('user_shelves', 'to-read')
        if not shelf:
            shelf = 'to-read'

        # Get ISBN from description
        description = entry.get('description', '') or entry.get('summary', '')
        isbn13 = extract_isbn(description)

        # Also check for isbn field directly
        if not isbn13:
            isbn13 = entry.get('isbn13') or entry.get('isbn')

        # Parse date added
        date_added = parse_goodreads_date(entry.get('user_date_added') or entry.get('published'))

        books.append(GoodreadsBook(
            goodreads_id=goodreads_id or '',
            title=title,
            author=author,
            isbn13=isbn13,
            cover_url=cover_url,
            date_added=date_added,
            shelf=shelf,
        ))

    return books


def validate_rss_url(url: str) -> bool:
    """Validate that a URL looks like a Goodreads RSS feed."""
    if not url:
        return False
    return 'goodreads.com' in url and ('list_rss' in url or 'rss' in url)


def normalize_goodreads_input(input_str: str) -> str:
    """
    Convert various Goodreads inputs to an RSS feed URL.

    Accepts:
    - Full RSS URL: https://www.goodreads.com/review/list_rss/12345?shelf=to-read
    - Profile URL: https://www.goodreads.com/user/show/12345678-username
    - Just the user ID: 12345678

    Returns RSS feed URL for the to-read shelf.
    """
    input_str = input_str.strip()

    # Already an RSS URL
    if 'list_rss' in input_str:
        return input_str

    # Extract user ID from various formats
    user_id = None

    # Profile URL: goodreads.com/user/show/12345678-username
    match = re.search(r'user/show/(\d+)', input_str)
    if match:
        user_id = match.group(1)

    # Just a number
    if not user_id and re.match(r'^\d+$', input_str):
        user_id = input_str

    # URL with just numbers at the end
    if not user_id:
        match = re.search(r'/(\d+)(?:-|$)', input_str)
        if match:
            user_id = match.group(1)

    if user_id:
        # Construct RSS URL for to-read shelf
        return f"https://www.goodreads.com/review/list_rss/{user_id}?shelf=to-read"

    # If nothing matched, return as-is and let it fail later
    return input_str
