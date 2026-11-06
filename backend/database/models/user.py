from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, UniqueConstraint
from datetime import datetime
from ..connection import Base


class UserModel(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, nullable=False, unique=True, index=True)  # lưu dạng chữ thường
    display_name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)  # bcrypt
    role = Column(String, nullable=False, default="user")  # user | admin
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime)


class AuthTokenModel(Base):
    __tablename__ = "auth_tokens"

    token_hash = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)


class UserDataModel(Base):

    __tablename__ = "user_data"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_user_data_key"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    key = Column(String, nullable=False)
    value_json = Column(Text, nullable=False, default="null")
    updated_at = Column(DateTime, default=datetime.utcnow)
