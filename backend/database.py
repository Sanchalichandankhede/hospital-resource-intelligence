from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.config import DATABASE_URL

# Configure engine options (SQLite requires check_same_thread=False)
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

def get_db():
    """
    FastAPI dependency that yields a database session and ensures it closes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
