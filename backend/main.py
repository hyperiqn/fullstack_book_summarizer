# main.py 
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, status, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.session import get_db, engine 
from app.db.base import create_all_tables
from app.db.models import User
from app.services.s3_service import s3_service
from app.schemas.document import DocumentResponse, DocumentCreate 
from app.core.security import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
import os
from datetime import datetime
from app.api.v1.api import api_router
from app.tasks.celery_app import celery_app
from app.tasks.pdf_processing_tasks import process_pdf_task



@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application startup event triggered. Initializing database...")
    try:
        await create_all_tables(engine)
        async with AsyncSession(engine) as session:
             from app.db.models import User
             existing_user = await session.get(User, 1)
             if not existing_user:
                from app.core.security import get_password_hash
                dummy_hashed_password = get_password_hash("testpassword")
                dummy_user = User(
                    id=1,
                    email="testuser@example.com",
                    hashed_password=dummy_hashed_password,
                    is_active=True
                )
                session.add(dummy_user)
                await session.commit()
                await session.refresh(dummy_user)
                print("Created dummy user with ID 1 (testuser@example.com) for testing.")
        print("Database initialization complete.")
    except Exception as e:
        print(f"Error during database initialization: {e}")
    yield
    print("Application shutdown event triggered.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG_MODE,
    version="0.1.0",
    lifespan=lifespan
)

origins = [
    "http://localhost",
    "http://localhost:3000", 
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,        
    allow_credentials=True,       
    allow_methods=["*"],          
    allow_headers=["*"],         
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def read_root():
    return {"message": f"Welcome to the {settings.PROJECT_NAME} backend!"}

@app.get("/health")
async def health_check(db_session=Depends(get_db)):
    return {"status": "ok", "database_connected": True}
