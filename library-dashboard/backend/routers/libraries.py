from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from models import get_db, User, Library, LibraryCreate, LibraryUpdate, LibraryResponse
from utils import encrypt_value, decrypt_value

router = APIRouter(prefix="/api/libraries", tags=["libraries"])

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


@router.get("", response_model=List[LibraryResponse])
async def get_libraries(db: Session = Depends(get_db)):
    """Get all configured libraries."""
    user = get_or_create_default_user(db)
    libraries = db.query(Library).filter(Library.user_id == user.id).all()
    return libraries


@router.post("", response_model=LibraryResponse)
async def add_library(library: LibraryCreate, db: Session = Depends(get_db)):
    """Add a new library configuration."""
    user = get_or_create_default_user(db)

    # Check for duplicate
    existing = db.query(Library).filter(
        Library.user_id == user.id,
        Library.base_url == library.base_url
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Library with this URL already exists")

    # Encrypt sensitive data
    encrypted_card = encrypt_value(library.card_number) if library.card_number else None
    encrypted_pin = encrypt_value(library.pin) if library.pin else None

    db_library = Library(
        user_id=user.id,
        name=library.name,
        base_url=library.base_url.rstrip('/'),
        card_number=encrypted_card,
        pin=encrypted_pin,
        is_active=library.is_active
    )

    db.add(db_library)
    db.commit()
    db.refresh(db_library)

    return db_library


@router.put("/{library_id}", response_model=LibraryResponse)
async def update_library(library_id: int, library: LibraryUpdate, db: Session = Depends(get_db)):
    """Update a library configuration."""
    user = get_or_create_default_user(db)

    db_library = db.query(Library).filter(
        Library.id == library_id,
        Library.user_id == user.id
    ).first()

    if not db_library:
        raise HTTPException(status_code=404, detail="Library not found")

    if library.name is not None:
        db_library.name = library.name
    if library.base_url is not None:
        db_library.base_url = library.base_url.rstrip('/')
    if library.card_number is not None:
        db_library.card_number = encrypt_value(library.card_number)
    if library.pin is not None:
        db_library.pin = encrypt_value(library.pin)
    if library.is_active is not None:
        db_library.is_active = library.is_active

    db.commit()
    db.refresh(db_library)

    return db_library


@router.delete("/{library_id}")
async def delete_library(library_id: int, db: Session = Depends(get_db)):
    """Delete a library configuration."""
    user = get_or_create_default_user(db)

    db_library = db.query(Library).filter(
        Library.id == library_id,
        Library.user_id == user.id
    ).first()

    if not db_library:
        raise HTTPException(status_code=404, detail="Library not found")

    db.delete(db_library)
    db.commit()

    return {"message": "Library deleted"}
