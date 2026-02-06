from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime


# Library schemas
class LibraryBase(BaseModel):
    name: str
    base_url: str
    card_number: Optional[str] = None
    is_active: bool = True


class LibraryCreate(LibraryBase):
    pin: Optional[str] = None


class LibraryUpdate(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    card_number: Optional[str] = None
    pin: Optional[str] = None
    is_active: Optional[bool] = None


class LibraryResponse(LibraryBase):
    id: int
    library_type: str

    class Config:
        from_attributes = True


# Book schemas
class BookBase(BaseModel):
    title: str
    author: Optional[str] = None
    isbn13: Optional[str] = None
    cover_url: Optional[str] = None
    shelf: str = "to-read"


class BookCreate(BookBase):
    goodreads_id: Optional[str] = None
    date_added: Optional[datetime] = None


class BookResponse(BookBase):
    id: int
    goodreads_id: Optional[str]
    date_added: Optional[datetime]

    class Config:
        from_attributes = True


# Availability schemas
class AvailabilityBase(BaseModel):
    status: str
    search_url: Optional[str] = None
    libby_url: Optional[str] = None  # share.libbyapp.com link


class AvailabilityResponse(AvailabilityBase):
    book_id: int
    library_id: int
    library_name: str
    checked_at: datetime

    class Config:
        from_attributes = True


class BookWithAvailability(BookResponse):
    availability: List[AvailabilityResponse] = []


# Goodreads schemas
class GoodreadsSyncRequest(BaseModel):
    rss_url: str


class GoodreadsSyncResponse(BaseModel):
    books_synced: int
    books: List[BookResponse]


# Availability check schemas
class AvailabilityCheckRequest(BaseModel):
    book_id: int


class AvailabilityCheckAllResponse(BaseModel):
    job_id: str
    message: str


# Checkout schemas
class CheckoutRequest(BaseModel):
    book_id: int
    library_id: int


class CheckoutResponse(BaseModel):
    success: bool
    message: str
    action_taken: Optional[str] = None
