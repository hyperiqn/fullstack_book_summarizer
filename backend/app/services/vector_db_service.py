# app/services/vector_db_service.py
import chromadb
import logging
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

CHROMA_DATA_PATH = "chroma_data"

class VectorDBService:
    def __init__(self):
        try:
            # self.client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
            self.client = chromadb.HttpClient(host="localhost", port=8000)
            logger.info(f"ChromaDB client initialized (HTTPCLIENT). Data will be stored at: {CHROMA_DATA_PATH}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {e}")
            self.client = None

    def get_or_create_collection(self, collection_name: str):
        if self.client is None:
            logger.error("ChromaDB client not initialized. Cannot get or create collection.")
            return None
        try:
            collection = self.client.get_or_create_collection(name=collection_name)
            logger.info(f"Accessed/Created ChromaDB collection: {collection_name}.")
            return collection
        except Exception as e:
            logger.error(f"Failed to get or create collection: {collection_name} : {e}.")
            return None
        
    def add_chunks_to_collection(
            self,
            collection,
            texts: List[str],
            embeddings: List[List[float]],
            metadatas: Optional[List[Dict[str, Any]]] = None,
            ids: Optional[List[str]] = None
    ):
        if collection is None:
            logger.error("Invalid ChromaDB collection. Cannot add chunks.")
            return
        
        if ids is None:
            ids = [f"chunk_{i}" for i in range(len(texts))]
        
        elif len(ids) != len(texts):
            logger.error("Number of IDs does not match number of texts.")
            return
        
        if len(texts) != len(embeddings):
            logger.error("Number of texts must match number of embeddings.")
            return
        
        try:
            collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Added {len(texts)} chunks to collection {collection.name}.")
        except Exception as e:
            logger.error(f"Failed to add chunks to collection: {collection.name} : {e}")

    def query_collection(
        self,
        collection,
        query_embeddings: List[List[float]],
        n_results: int = 5,
        where_clause: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        if collection is None:
            logger.error("Invalid ChromaDB collection. Cannot query.")
            return []
        try:
            results = collection.query(
                query_embeddings=query_embeddings,
                n_results=n_results,
                where=where_clause,
                include=['documents', 'distances', 'metadatas']
            )
            logger.info(f"Queried collection {collection.name}, found {len(results['documents'][0])} results.")
            formatted_results = []
            if results and results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    formatted_results.append({
                        "id": results['ids'][0][i],
                        "document": results['documents'][0][i],
                        "distance": results['distances'][0][i],
                        "metadata": results['metadatas'][0][i]
                    })
            return formatted_results
        except Exception as e:
            logger.error(f"Failed to query collection: {collection.name} : {e}")
            return []
        
    def delete_collection(self, collection_name: str) -> bool:
        if self.client is None:
            logger.error("ChromaDB client not initialized. Cannot delete collection.")
            return False
        try:
            self.client.delete_collection(name=collection_name)
            logger.info(f"Successfully deleted ChromaDB collection: {collection_name}.")
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection {collection_name} from ChromaDB: {e}")
            return False
        
vector_db_service = VectorDBService()

