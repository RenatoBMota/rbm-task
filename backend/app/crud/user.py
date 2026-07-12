from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import hash_password


def get_user(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
    return db.query(User).offset(skip).limit(limit).all()


def create_user(db: Session, user_in: UserCreate) -> User:
    is_first_user = db.query(User).count() == 0
    db_user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hash_password(user_in.password),
        role=UserRole.ADMIN if is_first_user else UserRole.MEMBER,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user: User, user_in: UserUpdate) -> User:
    update_data = user_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


def update_user_role(db: Session, user: User, role: UserRole) -> User:
    user.role = role
    db.commit()
    db.refresh(user)
    return user
