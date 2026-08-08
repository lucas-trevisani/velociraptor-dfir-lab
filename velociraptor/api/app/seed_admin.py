import os

from sqlalchemy import select

from .database import Base, SessionLocal, engine
from .models import User, UserRole
from .security import hash_password


def main() -> None:
    email = os.environ["ADMIN_EMAIL"]
    password = os.environ["ADMIN_PASSWORD"]
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user:
            print("Admin already exists")
            return
        db.add(User(email=email, password_hash=hash_password(password), role=UserRole.admin))
        db.commit()
        print("Admin created")


if __name__ == "__main__":
    main()

