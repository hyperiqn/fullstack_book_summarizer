# app/schemas/document.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

from app.db.models import DocumentStatus


class DocumentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)

class DocumentCreate(DocumentBase):
    pass

class DocumentResponse(DocumentBase):
    id: int
    file_path: str
    file_size_bytes: Optional[int] = None
    upload_timestamp: datetime
    processing_status: DocumentStatus
    summary: Optional[str] = None
    owner_id: int

    class Config:
        from_attributes = True