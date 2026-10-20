from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from .config import DATABASE_URL, DATA_DIR
from .models import Base
import os

os.makedirs(DATA_DIR, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 20} if "sqlite" in DATABASE_URL else {},
    echo=False
)

SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
ScopedSession = scoped_session(SessionFactory)

def init_db(custom_engine=None):
    global engine, SessionFactory
    target_engine = custom_engine or engine
    if custom_engine is not None:
        engine = custom_engine
        SessionFactory.configure(bind=custom_engine)
    Base.metadata.create_all(bind=target_engine)

    # Automatic non-destructive column migration for SQLite
    try:
        from sqlalchemy import text
        with target_engine.connect() as conn:
            res = conn.execute(text("PRAGMA table_info(patients);"))
            columns = [row[1] for row in res.fetchall()]
            if "email" not in columns and len(columns) > 0:
                conn.execute(text("ALTER TABLE patients ADD COLUMN email VARCHAR(120);"))
                conn.commit()
    except Exception:
        pass

def get_session():
    return ScopedSession()
