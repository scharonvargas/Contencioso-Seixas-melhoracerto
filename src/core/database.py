"""
src/core/database.py
Gerenciamento de conexões e sessões de banco de dados.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.core.config import settings
from src.models.entities import Base

db_url = settings.DATABASE_URL
if "sqlite" in db_url:
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
else:
    engine = create_engine(db_url, pool_pre_ping=True, pool_size=20, max_overflow=10)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from sqlalchemy import text

def init_db():
    Base.metadata.create_all(bind=engine)
    # Garante migração de colunas adicionadas em SQLite
    with engine.connect() as conn:
        for col_def in [
            "ALTER TABLE evaluations ADD COLUMN rules_results JSON",
            "ALTER TABLE document_pages ADD COLUMN document_name VARCHAR(255)",
            "ALTER TABLE document_pages ADD COLUMN page_in_document INTEGER",
            "ALTER TABLE document_pages ADD COLUMN segment_type VARCHAR(64)",
            "ALTER TABLE document_pages ADD COLUMN raw_text TEXT",
            "ALTER TABLE document_pages ADD COLUMN words_data JSON"
        ]:
            try:
                conn.execute(text(col_def))
                conn.commit()
            except Exception:
                pass # Coluna já existe

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Executa inicialização e migração ao importar o módulo
init_db()
