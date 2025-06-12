# app/tasks/pdf_processing_tasks.py
from app.tasks.celery_app import celery_app
from app.services.s3_service import s3_service
from app.services.embedding_service import embedding_service
from app.services.vector_db_service import vector_db_service
from app.services.llm_service import llm_service 
from app.db.session import get_db_sync
from app.db.models import Document, DocumentStatus
import os
import tempfile
import fitz
from langchain_text_splitters import RecursiveCharacterTextSplitter 
from urllib.parse import urlparse, unquote
import asyncio

@celery_app.task(name="process_pdf_task", bind=True) 
def process_pdf_task(self, document_id: int):
    print(f"Starting PDF processing task for document_id: {document_id}")

    def update_processing_progress(stage, current_progress):
        self.update_state(state='PROGRESS',
                          meta={'stage': stage, 'current_progress': current_progress})
        print(f"Document {document_id} progress: {stage} - {current_progress}%")


    with get_db_sync() as db:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            print(f"Document with ID {document_id} not found.")
            return

        print(f"Processing document: {document.title} from S3 path: {document.file_path}")

        document.processing_status = DocumentStatus.PROCESSING
        db.add(document)
        db.commit()
        db.refresh(document)
        update_processing_progress("Initializing", 5) 


        temp_pdf_path = None
        try:
            # 1. Download PDF from S3
            update_processing_progress("Downloading from S3", 10)
            parsed_url = urlparse(document.file_path)
            object_name = unquote(parsed_url.path.lstrip('/'))

            if not object_name:
                raise ValueError(f"Could not extract S3 object name from URL: {document.file_path}")

            print(f"Attempting to download S3 object: {object_name}...")

            pdf_content_bytes = asyncio.run(s3_service.download_file(object_name))

            if pdf_content_bytes is None:
                raise RuntimeError(f"Failed to retrieve content for {object_name} from S3.")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_pdf_path = temp_file.name
                temp_file.write(pdf_content_bytes) 
            print(f"Downloaded PDF content and saved to temporary path: {temp_pdf_path}")
            update_processing_progress("Download complete", 20)

            # 2. Extract Text from PDF
            update_processing_progress("Extracting text", 30)
            full_text = ""
            try:
                doc = fitz.open(temp_pdf_path)
                for page in doc:
                    full_text += page.get_text()
                doc.close()
                print(f"Extracted {len(full_text)} characters from PDF.")
                if not full_text.strip():
                    raise ValueError("Extracted text is empty or only whitespace.")
            except Exception as e:
                raise RuntimeError(f"Failed to extract text from PDF: {e}")
            update_processing_progress("Text extraction complete", 40)

            update_processing_progress("Generating summary", 45)

            summary = asyncio.run(llm_service.generate_summary(full_text, max_input_tokens=30000)) 
            if summary:
                document.summary = summary
                db.add(document)
                db.commit()
                db.refresh(document)
                print(f"Generated and saved summary for document {document.id}.")
            else:
                print(f"Failed to generate summary for document {document.id}.")
            update_processing_progress("Summary generation complete", 48)


            # 3. Chunk Text (for RAG embeddings - this is separate from summarization chunking)
            update_processing_progress("Chunking text for RAG", 50)
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len, 
                is_separator_regex=False,
            )
            chunks = text_splitter.split_text(full_text)
            print(f"Split document into {len(chunks)} chunks for RAG.")
            if not chunks:
                raise ValueError("No chunks generated from the document text for RAG.")
            update_processing_progress("Text chunking for RAG complete", 60)

            # 4. Generating embeddings for chunks
            update_processing_progress("Generating embeddings", 70)
            print(f"Generating embeddings for {len(chunks)} chunks...")
            chunk_embeddings = embedding_service.get_embeddings(chunks)
            if not chunk_embeddings:
                raise RuntimeError("Failed to generate embeddings for chunks.")
            print(f"Generated {len(chunk_embeddings)} embeddings.")
            update_processing_progress("Embeddings generated", 80)

            # 5. Store Chunks and Embeddings in ChromaDB
            update_processing_progress("Storing in vector DB", 90)
            collection_name = f"doc_{document.id}"
            print(f"Attempting to create ChromaDB collection: {collection_name}")
            collection = vector_db_service.get_or_create_collection(collection_name)
            if collection is None:
                raise RuntimeError(f"Failed to get or create ChromaDB collection: {collection_name}.")
            print(f"ChromaDB collection '{collection_name}' created/obtained successfully.")

            metadatas = [{"document_id": document.id} for _ in chunks]
            chunk_ids = [f"doc_{document_id}_chunk_{i}" for i in range(len(chunks))]
            print("Generated metadatas and chunk_ids. Adding chunks to ChromaDB...")
            vector_db_service.add_chunks_to_collection(
                collection=collection,
                texts=chunks,
                embeddings=chunk_embeddings,
                metadatas=metadatas,
                ids=chunk_ids
            )
            print(f"Successfully added chunks to ChromaDB collection: '{collection_name}'.")
            update_processing_progress("Vector DB storage complete", 95)

            # 6. Update document status
            document.processing_status = DocumentStatus.COMPLETED
            db.add(document)
            db.commit()
            db.refresh(document)
            print(f"Document {document.id} status updated to COMPLETED after processing.")
            update_processing_progress("Processing completed", 100) 

        except Exception as e:
            print(f"Error processing document {document_id}: {e}")
            document.processing_status = DocumentStatus.FAILED
            db.add(document)
            db.commit()
            db.refresh(document)
            self.update_state(state='FAILED', meta={'exc': str(e), 'current_progress': 0})
        finally:
            if temp_pdf_path and os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
                print(f"Cleaned up temporary PDF file: {temp_pdf_path}")

    print(f"Finished PDF processing task for document_id: {document_id}")