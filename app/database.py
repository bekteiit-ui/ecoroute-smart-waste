"""Veritabanı bağlantısı.

DATABASE_URL ortam değişkeni ile hedef veritabanı seçilir:

    # Bulut PostgreSQL (Supabase / Neon)
    DATABASE_URL=postgresql+psycopg2://kullanici:sifre@host:5432/ecoroute?sslmode=require

    # MS SQL Server
    DATABASE_URL=mssql+pyodbc://kullanici:sifre@host:1433/ecoroute?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes

Tanımlı değilse yerel geliştirme için SQLite dosyası kullanılır.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ecoroute.db")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
_engine_kwargs = {"pool_pre_ping": True}
if DATABASE_URL.startswith("mssql"):
    # pyodbc için toplu INSERT hızlandırma
    _engine_kwargs["fast_executemany"] = True

engine = create_engine(DATABASE_URL, connect_args=_connect_args, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI bağımlılığı: istek başına bir oturum açar ve kapatır."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
