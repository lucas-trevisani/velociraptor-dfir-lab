import base64
import hashlib
import hmac
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import jwt
from passlib.context import CryptContext

from .config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str, role: str) -> tuple[str, str, datetime]:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    jti = uuid.uuid4().hex
    token = jwt.encode(
        {"sub": subject, "role": role, "jti": jti, "exp": expires_at},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return token, jti, expires_at


def decode_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def constant_time_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)


def load_private_key():
    key_data = Path(get_settings().rsa_private_key_path).read_bytes()
    return serialization.load_pem_private_key(key_data, password=None)


def load_public_key_pem() -> str:
    return Path(get_settings().rsa_public_key_path).read_text(encoding="utf-8")


def sign_bytes(data: bytes) -> bytes:
    private_key = load_private_key()
    return private_key.sign(data, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())


def aes_key() -> bytes:
    return base64.b64decode(get_settings().aes_key_base64)


def encrypt_bytes(data: bytes) -> bytes:
    nonce = os.urandom(12)
    encrypted = AESGCM(aes_key()).encrypt(nonce, data, None)
    return nonce + encrypted


def decrypt_bytes(data: bytes) -> bytes:
    nonce, encrypted = data[:12], data[12:]
    return AESGCM(aes_key()).decrypt(nonce, encrypted, None)


def random_license_key() -> str:
    return "VL-" + base64.urlsafe_b64encode(os.urandom(24)).decode("ascii").rstrip("=")
