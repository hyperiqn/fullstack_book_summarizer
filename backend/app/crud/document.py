# app/crud/document.py
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Document, User, DocumentStatus
from app.schemas.document import DocumentCreate
from typing import Optional

async def create_document(
    db: AsyncSession,
    document_in: DocumentCreate,
    file_path: str,
    file_size_bytes: int,
    owner_id: int
) -> Document:
    db_obj = Document(
        title=document_in.title,
        file_path=file_path,
        file_size_bytes=file_size_bytes,
        owner_id=owner_id,
        processing_status=DocumentStatus.PENDING
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def delete_document(db: AsyncSession, document_id: int) -> None:
    document_to_delete = await db.get(Document, document_id)
    if document_to_delete:
        await db.delete(document_to_delete)
        await db.commit()
        print(f"Deleted document: {document_to_delete}.")
    else:
        print(f"Warning: Document with ID {document_id} not found for deletion in DB.")

async def get_document_by_id(db: AsyncSession, document_id: int) -> Optional[Document]:
    return await db.get(Document, document_id)
