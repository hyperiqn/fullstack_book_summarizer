# app/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from app.core.config import settings
from contextlib import contextmanager

from app.core.config import settings 

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG_MODE, future=True)

AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

sync_engine = create_engine(settings.DATABASE_URL.replace("+asyncpg", ""), echo=False)
SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
    class_=Session
)

@contextmanager
def get_db_sync():
    session = SyncSessionLocal()
    try:
        yield session
    finally:
        session.close()