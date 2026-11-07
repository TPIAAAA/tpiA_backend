from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import create_engine, String, DateTime, JSON, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from app.core.config import DATABASE_URL


connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
# pool_recycle protects against MySQL idle connection timeout; SQLite CI remains supported.
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600,
                       connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Experiment(Base):
    __tablename__ = "experiments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    seed: Mapped[int] = mapped_column(Integer)
    model_json: Mapped[dict] = mapped_column(JSON)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


def init_db():
    Base.metadata.create_all(engine)  # 教學起始版；正式改 Alembic migration


def get_db():
    with SessionLocal() as session:
        yield session
