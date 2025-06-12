# app/db/base.py
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import MetaData

# This is the base class that all your SQLAlchemy models will inherit from.
# It connects your Python classes to your database tables.
Base = declarative_base()

# Import all models here so that Base.metadata.create_all knows about them
# This import is necessary for Alembic migrations and for creating tables
# Make sure to import all your models here as you add them
from app.db import models # noqa: F401 (This is a common way to suppress unused import warnings,
                          # as the import is for Base.metadata to find the models)

async def create_all_tables(engine: AsyncEngine):
    async with engine.begin() as conn:
        # Pass Base.metadata directly to run_sync to create all tables registered with Base
        await conn.run_sync(Base.metadata.create_all)