"""
src/core/database.py
Gerenciamento de conexões e sessões de banco de dados.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.core.config import settings
from src.models.entities import Base

from sqlalchemy import event

db_url = settings.DATABASE_URL
if "sqlite" in db_url:
    engine = create_engine(db_url, connect_args={"check_same_thread": False, "timeout": 30})

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()
else:
    engine = create_engine(db_url, pool_pre_ping=True, pool_size=20, max_overflow=10)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from sqlalchemy import text

_initialized = False

def init_db():
    global _initialized
    if not _initialized:
        Base.metadata.create_all(bind=engine)
        _initialized = True


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Executa inicialização e migração ao importar o módulo
init_db()
