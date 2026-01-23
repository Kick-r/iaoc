# db.py
import os
from datetime import datetime

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# =========================
# DB URL (Render / Postgres)
# =========================
DB_URL = os.getenv("DATABASE_URL")

if not DB_URL:
    raise RuntimeError("DATABASE_URL não configurada (Render env var)")

# Render usa postgres://, SQLAlchemy exige postgresql://
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DB_URL,
    pool_pre_ping=True,   # evita conexão morta após sleep do Render
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)

Base = declarative_base()


# =========================
# MODELS
# =========================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)

    # Nome exibido
    name = Column(String(80), nullable=True)

    # Auth
    email = Column(String(255), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)

    # Perfil pra IA
    age = Column(Integer, nullable=True)
    context = Column(Text, nullable=True)
    goal = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    chats = relationship(
        "Chat",
        back_populates="user",
        cascade="all, delete-orphan"
    )


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(120), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="chats")
    messages = relationship(
        "Message",
        back_populates="chat",
        cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    role = Column(String(20), nullable=False)   # user | assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    chat = relationship("Chat", back_populates="messages")


def init_db():
    Base.metadata.create_all(bind=engine)
