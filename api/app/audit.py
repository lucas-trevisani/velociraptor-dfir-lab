from fastapi import Request
from sqlalchemy.orm import Session

from .models import Log, User


def write_log(db: Session, request: Request | None, event: str, payload: dict, user: User | None = None) -> None:
    ip = request.client.host if request and request.client else None
    db.add(Log(actor_user_id=user.id if user else None, event=event, ip_address=ip, payload=payload))

