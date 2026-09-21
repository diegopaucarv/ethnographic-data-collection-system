"""Authentication and authorization utilities."""
import os
import hashlib
import uuid
from typing import Optional
from datetime import datetime, timedelta
import jwt
from database import fetchrow, execute


SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable must be set")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours


def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    salt = os.urandom(32)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt, 100000
    )
    return (salt + pwd_hash).hex()


def verify_password(stored_hash: str, password: str) -> bool:
    """Verify a password against its hash."""
    try:
        salt = bytes.fromhex(stored_hash[:64])
        stored_pwd_hash = bytes.fromhex(stored_hash[64:])
        pwd_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt, 100000
        )
        return pwd_hash == stored_pwd_hash
    except Exception:
        return False


def create_access_token(user_id: str, role: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    expire = datetime.utcnow() + expires_delta
    to_encode = {
        "sub": user_id,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        
        if user_id is None or role is None:
            return None
        
        return {"user_id": user_id, "role": role}
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def create_user(email: str, name: str, password: str, role: str = "collector") -> dict:
    """Create a new user."""
    user_id = str(uuid.uuid4())
    password_hash = hash_password(password)
    
    query = """
    INSERT INTO users (id, email, name, password_hash, role, created_at, updated_at)
    VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    RETURNING id, email, name, role, created_at, updated_at
    """
    
    user = await fetchrow(query, user_id, email, name, password_hash, role)
    return user


async def authenticate_user(email: str, password: str) -> Optional[dict]:
    """Authenticate a user by email and password."""
    user = await fetchrow(
        "SELECT id, email, name, role, password_hash FROM users WHERE email = $1",
        email
    )
    
    if not user:
        return None
    
    if not verify_password(user["password_hash"], password):
        return None
    
    # Remove password hash from response
    del user["password_hash"]
    return user


async def get_user(user_id: str) -> Optional[dict]:
    """Get a user by ID."""
    return await fetchrow(
        "SELECT id, email, name, role, created_at, updated_at FROM users WHERE id = $1",
        user_id
    )


async def is_admin(user_id: str) -> bool:
    """Check if a user is an admin."""
    user = await get_user(user_id)
    return user is not None and user.get("role") == "admin"
