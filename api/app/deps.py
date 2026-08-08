from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import Session as AuthSession
from .models import User
from .security import decode_token


def current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    payload = decode_token(authorization.removeprefix("Bearer ").strip())
    user_id = UUID(payload["sub"])
    auth_session = db.scalar(select(AuthSession).where(AuthSession.jti == payload["jti"], AuthSession.revoked_at.is_(None)))
    user = db.get(User, user_id)
    if not auth_session or not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user

