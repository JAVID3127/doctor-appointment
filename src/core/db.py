from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from .config import DATABASE_URL, DATA_DIR
from .models import Base
import os

os.makedirs(DATA_DIR, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False
)

SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
ScopedSession = scoped_session(SessionFactory)

def init_db(custom_engine=None):
    target_engine = custom_engine or engine
    Base.metadata.create_all(bind=target_engine)

def get_session():
    return ScopedSession()
