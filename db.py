from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

DB_URL = "sqlite:///maggie.db"

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)

    # Nome exibido
    name = Column(String(80), nullable=True)

    # Login/Cadastro
    # (nullable=True pra não quebrar usuário MVP antigo. No signup/login a gente exige.)
    email = Column(String(255), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)

    # Perfil que a IA usa
    age = Column(Integer, nullable=True)
    context = Column(Text, nullable=True)
    goal = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(120), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    role = Column(String(20), nullable=False)   # "user" | "assistant"
    content = Column(Text, nullable=False)      # pode ser texto/HTML
    created_at = Column(DateTime, default=datetime.utcnow)

    chat = relationship("Chat", back_populates="messages")


def init_db():
    Base.metadata.create_all(bind=engine)

###eu gostaria de lhe perguntar uma coisa. Oh pai. O render, quando o site fica inativo por algumas horas, ele meio que fecha, ele fica inativo e aí quando você acessa o site novamente, ele meio que reinicia. Então, tipo, todos os dados do banco é perdido. Por que isso que eu tô achando, porque tipo, eu tentei acessar, ontem eu criei uma senha com o meu e-mail, aí hoje eu acessei, coloquei minha senha e não tava entrando. Tipo, é como se... E como eu acho isso? Porque eu criei outro usuário com o mesmo e-mail e falei ainda eu fiz existe isso, já é um usuário com o meu e-mail, entendeu? Ele não ia deixar. Me responde isso aí, amigos, de tudo.