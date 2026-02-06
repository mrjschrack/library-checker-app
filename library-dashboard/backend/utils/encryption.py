from cryptography.fernet import Fernet
import os
import base64

# Get or generate encryption key
# In production, this should be set via environment variable
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    # Generate a key for development (will be lost on restart)
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    print(f"Warning: Using generated encryption key. Set ENCRYPTION_KEY env var for persistence.")


def get_fernet() -> Fernet:
    """Get Fernet instance for encryption/decryption."""
    key = ENCRYPTION_KEY
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def encrypt_value(value: str) -> str:
    """Encrypt a string value."""
    if not value:
        return value
    f = get_fernet()
    encrypted = f.encrypt(value.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_value(encrypted_value: str) -> str:
    """Decrypt an encrypted string value."""
    if not encrypted_value:
        return encrypted_value
    try:
        f = get_fernet()
        decoded = base64.urlsafe_b64decode(encrypted_value.encode())
        decrypted = f.decrypt(decoded)
        return decrypted.decode()
    except Exception:
        # If decryption fails, return the original value (might not be encrypted)
        return encrypted_value
