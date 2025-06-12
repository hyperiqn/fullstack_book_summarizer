# fullstack_rag/backend/app/api/v1/endpoints/documents.py
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session, selectinload 
from sqlalchemy.ext.asyncio import AsyncSession 
from sqlalchemy import select
from celery.result import AsyncResult

from app.db.session import get_db
from app.db.models import Document, DocumentStatus, User
from app.crud.document import create_document, delete_document as crud_delete_document
from app.crud import document as crud_document
from app.services.s3_service import s3_service
from app.tasks.pdf_processing_tasks import process_pdf_task
from app.core.security import get_current_user 

from app.services.embedding_service import embedding_service
from app.services.vector_db_service import vector_db_service
from app.services.llm_service import llm_service
from app.services.reranker_service import reranker_service
from app.schemas.document import DocumentResponse, DocumentCreate

router = APIRouter()

@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    title: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    print(f"User {current_user.email} (ID: {current_user.id}) is uploading document: {title}")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload a pdf."
        )

    timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S%f")
    file_extension = os.path.splitext(file.filename)[1] if '.' in file.filename else ''
    object_name = f"raw_pdfs/{timestamp_str}_{title.replace(' ', '_')}{file_extension}"
    file_size_bytes = file.size

    s3_url = await s3_service.upload_file(file, object_name)

    if not s3_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file to S3."
        )

    try:
        new_document = await create_document(
            db=db,
            document_in=DocumentCreate(title=title),
            file_path=s3_url,
            file_size_bytes=file_size_bytes,
            owner_id=current_user.id
        )
        task = process_pdf_task.delay(new_document.id)
        new_document.celery_task_id = task.id 
        db.add(new_document) 
        await db.commit()
        await db.refresh(new_document)
        print(f"Dispatched process_pdf_task for document ID: {new_document.id}")

        return new_document

    except Exception as e:
        await s3_service.delete_file(object_name)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save document metadata to database: {e}"
        )

@router.get("/{document_id}/query/", response_model=Dict[str, Any]) 
async def query_document(
    document_id: int,
    query_text: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Verify document existence and ownership
    document = await db.get(Document, document_id)

    if not document or document.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or you don't have access to it."
        )

    if document.processing_status != DocumentStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document is not yet processed. Current status: {document.processing_status.value}. Please wait."
        )

    # 2. Get ChromaDB collection for the document
    collection_name = f"doc_{document.id}"
    collection = vector_db_service.get_or_create_collection(collection_name)
    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not access document's vector store."
        )
    
    # 3. Generate embedding for the query
    query_embeddings_raw = embedding_service.get_embeddings([query_text])
    if not query_embeddings_raw:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate embedding for the query."
        )

    query_embeddings_for_chroma = []
    for emb in query_embeddings_raw:
        if hasattr(emb, 'tolist'):
            query_embeddings_for_chroma.append(emb.tolist())
        else:
            query_embeddings_for_chroma.append(emb)

    # 4. Query ChromaDB for relevant chunks
    INITIAL_CHROMA_RESULTS = 10
    TOP_N_RERANKED_RESULTS = 5
    retrieved_chunks_for_reranking = vector_db_service.query_collection(
        collection=collection,
        query_embeddings=query_embeddings_for_chroma,
        n_results=INITIAL_CHROMA_RESULTS, 
    )

    if not retrieved_chunks_for_reranking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No relevant chunks found for this query in the document."
        )
    
    # 5 Rerank the retrieved chunks
    reranked_chunks_info = await reranker_service.rerank(
    query=query_text,
    documents=retrieved_chunks_for_reranking,
    top_n=TOP_N_RERANKED_RESULTS
    )
    if not reranked_chunks_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No relevant chunks found after re-ranking."
        )
    
    # 6. Construct RAG prompt with TOP N re-ranked chunks
    context_chunks = [chunk['document'] for chunk in reranked_chunks_info] 
    context_text = "\n\n".join(context_chunks)

    # 7. Construct the RAG prompt
    rag_prompt = f"""[INST] Use the following context to answer the question. If the answer is not in the context, say "I don't have enough information to answer that based on the provided document. You may elaborate and explain in greater detail if you think it's beneficial."

    Context:
    {context_text}

    Question: {query_text}

    Answer: [/INST]"""

    print(f"Sending prompt to LLM (first 500 chars):\n{rag_prompt[:500]}...") # Log first 500 chars of prompt

    # 8. Call the LLMService to generate a response
    llm_response = await llm_service.generate_text(rag_prompt)

    if not llm_response:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get a response from the Language Model."
        )

    # 9. Return the LLM's response and optionally include retrieved chunks
    return {
        "llm_answer": llm_response,
        "retrieved_chunks": reranked_chunks_info 
    }

@router.get("", response_model=List[DocumentResponse]) 
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Document)
        .where(Document.owner_id == current_user.id)
        .order_by(Document.upload_timestamp.desc())
    )
    documents = result.scalars().all()
    return documents

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Verify document existence and ownership
    document = await db.get(Document, document_id)

    if not document or document.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or you don't have access to it."
        )


    s3_object_name = document.file_path.split('.com/')[-1] 

    try:
        # 2. Delete from S3
        s3_deleted = await s3_service.delete_file(s3_object_name)
        if not s3_deleted:
            print(f"Warning: S3 file {s3_object_name} for document {document_id} might not have been deleted.")

        # 3. Delete from ChromaDB
        chroma_collection_name = f"doc_{document.id}"
        vector_db_service.delete_collection(chroma_collection_name)
        print(f"ChromaDB collection {chroma_collection_name} deleted (if it existed).")

        # 4. Delete from PostgreSQL
        await crud_delete_document(db, document_id)
        print(f"Document {document_id} deleted from PostgreSQL.")

        return 
    except Exception as e:
        print(f"Error during document deletion for {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document and its associated data: {e}"
        )

@router.get("/{document_id}/processing_status/", response_model=Dict[str, Any])
async def get_document_processing_status(
    document_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    document = await crud_document.get_document_by_id(db, document_id)
    if not document or document.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if document.processing_status == DocumentStatus.PROCESSING:
        celery_task_id = document.celery_task_id 
        if celery_task_id:
            task_result = AsyncResult(celery_task_id)
            state = task_result.state
            progress_meta = task_result.info if isinstance(task_result.info, dict) else {}

            return {
                "document_id": document.id,
                "db_status": document.processing_status,
                "celery_state": state,
                "processing_stage": progress_meta.get('stage', 'Unknown'),
                "current_progress": progress_meta.get('current_progress', 0)
            }
        else:
            return {
                "document_id": document.id,
                "db_status": document.processing_status,
                "celery_state": "PENDING", 
                "processing_stage": "Waiting for task to start",
                "current_progress": 0
            }
    else:
        return {
            "document_id": document.id,
            "db_status": document.processing_status,
            "celery_state": document.processing_status, 
            "processing_stage": document.processing_status.value,
            "current_progress": 100 if document.processing_status == DocumentStatus.COMPLETED else 0
        }