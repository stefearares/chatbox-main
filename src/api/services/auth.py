from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from db.models import UserRecord
from utils import security


def get_user_by_email(db: Session, email: str) -> Optional[UserRecord]:
    return db.query(UserRecord).filter(UserRecord.email == email).first()


def signup_user(
    db: Session, email: str, password: str, name: Optional[str] = None
) -> UserRecord:
    if get_user_by_email(db, email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered!"
        )

    user = UserRecord(
        email=email,
        name=name,
        password_hash=security.hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login_user(db: Session, email: str, password: str) -> UserRecord:
    user = get_user_by_email(db, email)

    if (
        not user
        or not user.password_hash
        or not security.verify_password(user.password_hash, password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password!",
        )

    return user
