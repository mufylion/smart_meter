import os
import bcrypt
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from dotenv import load_dotenv
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import base64

# Load environment variables
load_dotenv()

# Get secret keys from environment variables or use secure defaults
SECRET_KEY = os.getenv("JWT_SECRET_KEY", get_random_bytes(32).hex())

# Handle encryption key
env_key = os.getenv("ENCRYPTION_KEY")
if env_key:
    try:
        # If provided in env, should be base64 encoded
        ENCRYPTION_KEY = base64.b64decode(env_key)
        if len(ENCRYPTION_KEY) != 32:
            ENCRYPTION_KEY = hashlib.sha256(ENCRYPTION_KEY).digest()
    except:
        # If invalid, use a new random key
        ENCRYPTION_KEY = get_random_bytes(32)
else:
    # Generate a new random key
    ENCRYPTION_KEY = get_random_bytes(32)

TOKEN_ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 30

class SecurityUtils:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=TOKEN_ALGORITHM)

    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """Verify a JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[TOKEN_ALGORITHM])
            return payload
        except JWTError:
            return None

    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key"""
        return base64.b64encode(get_random_bytes(32)).decode()

    @staticmethod
    def encrypt_data(data: str) -> tuple[str, str]:
        """Encrypt data using AES"""
        cipher = AES.new(ENCRYPTION_KEY, AES.MODE_EAX)
        nonce = cipher.nonce
        ciphertext, tag = cipher.encrypt_and_digest(data.encode())
        return (
            base64.b64encode(nonce + ciphertext + tag).decode(),
            hashlib.sha256(data.encode()).hexdigest()
        )

    @staticmethod
    def decrypt_data(encrypted_data: str) -> Optional[str]:
        """Decrypt data using AES"""
        try:
            data = base64.b64decode(encrypted_data.encode())
            nonce = data[:16]
            tag = data[-16:]
            ciphertext = data[16:-16]
            
            cipher = AES.new(ENCRYPTION_KEY, AES.MODE_EAX, nonce=nonce)
            decrypted_data = cipher.decrypt_and_verify(ciphertext, tag)
            return decrypted_data.decode()
        except Exception as e:
            print(f"Decryption error: {str(e)}")
            return None

    @staticmethod
    def generate_transaction_id() -> str:
        """Generate a unique transaction ID"""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        random_suffix = get_random_bytes(4).hex()
        return f"TXN-{timestamp}-{random_suffix}"
