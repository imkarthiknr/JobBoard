"""User persistence and authentication. No HTTP concerns here."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models import User
from app.schemas.user import UserCreate

# A real bcrypt hash to compare against when the username doesn't exist, so a login
# attempt takes the same time either way (prevents username enumeration by timing).
_DUMMY_HASH = hash_password("timing-equaliser-not-a-real-password-1")


class DuplicateUserError(Exception):
    def __init__(self, field: str) -> None:
        super().__init__(f"{field} already registered")
        self.field = field


def get_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.username) == username.lower()))


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def create_user(db: Session, data: UserCreate, *, is_superuser: bool = False) -> User:
    if get_by_username(db, data.username):
        raise DuplicateUserError("username")
    if get_by_email(db, data.email):
        raise DuplicateUserError("email")
    user = User(
        username=data.username,
        email=data.email.lower(),
        hashed_password=hash_password(data.password),
        is_superuser=is_superuser,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, username: str, password: str) -> User | None:
    """Return the user if the credentials are valid and the account is active."""
    user = get_by_username(db, username)
    if user is None:
        # Hash anyway so response time doesn't reveal whether the username exists.
        verify_password(password, _DUMMY_HASH)
        return None
    if not user.is_active or not verify_password(password, user.hashed_password):
        return None
    return user
