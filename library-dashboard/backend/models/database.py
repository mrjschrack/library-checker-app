from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import StaticPool
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./library_dashboard.db")

# Handle SQLite - use StaticPool for better connection handling
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool  # Single connection reused - better for SQLite
    )
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    goodreads_rss_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    libraries = relationship("Library", back_populates="user", cascade="all, delete-orphan")
    books = relationship("Book", back_populates="user", cascade="all, delete-orphan")


class Library(Base):
    __tablename__ = "libraries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    base_url = Column(String(512), nullable=False)
    card_number = Column(String(255), nullable=True)  # Encrypted
    pin = Column(String(255), nullable=True)  # Encrypted
    library_type = Column(String(50), default="overdrive")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="libraries")
    availability_cache = relationship("AvailabilityCache", back_populates="library", cascade="all, delete-orphan")


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    goodreads_id = Column(String(50), nullable=True)
    title = Column(String(512), nullable=False)
    author = Column(String(255), nullable=True)
    isbn13 = Column(String(20), nullable=True)
    cover_url = Column(Text, nullable=True)
    date_added = Column(DateTime, nullable=True)
    shelf = Column(String(100), default="to-read")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="books")
    availability_cache = relationship("AvailabilityCache", back_populates="book", cascade="all, delete-orphan")


class AvailabilityCache(Base):
    __tablename__ = "availability_cache"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    library_id = Column(Integer, ForeignKey("libraries.id"), nullable=False)
    status = Column(String(50), nullable=False)  # available, hold, unavailable, unknown, not_found, error
    search_url = Column(Text, nullable=True)
    libby_url = Column(Text, nullable=True)  # share.libbyapp.com link
    checked_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    consecutive_failures = Column(Integer, default=0)

    book = relationship("Book", back_populates="availability_cache")
    library = relationship("Library", back_populates="availability_cache")


def init_db():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
