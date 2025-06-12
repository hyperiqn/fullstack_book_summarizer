# app/services/reranker_service.py
import logging
from typing import List, Dict, Any, Optional
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

RERANKER_MODEL_NAME = 'cross-encoder/ms-marco-MiniLM-L-6-v2' 

class ReRankerService:
    def __init__(self):
        try:
            self.model = CrossEncoder(RERANKER_MODEL_NAME)
            logger.info(f"ReRankerService initialized. Loaded model: {RERANKER_MODEL_NAME}")
        except Exception as e:
            logger.error(f"Failed to load re-ranker model {RERANKER_MODEL_NAME}: {e}")
            self.model = None

    async def rerank(self, query: str, documents: List[Dict[str, Any]], top_n: int = 3) -> List[Dict[str, Any]]:
        if self.model is None:
            logger.error("Re-ranker model not loaded. Cannot perform re-ranking.")
            return documents[:top_n] 

        if not documents:
            return []

        sentences_to_rerank = [(query, doc['document']) for doc in documents]

        try:
            scores = self.model.predict(sentences_to_rerank)

            scored_documents = []
            for i, doc in enumerate(documents):
                doc_with_score = doc.copy()
                doc_with_score['relevance_score'] = float(scores[i]) 
                scored_documents.append(doc_with_score)

            sorted_documents = sorted(scored_documents, key=lambda x: x['relevance_score'], reverse=True)

            logger.info(f"Re-ranked {len(documents)} documents. Returning top {top_n}.")
            return sorted_documents[:top_n]

        except Exception as e:
            logger.error(f"Error during re-ranking: {e}")
            return documents[:top_n]

reranker_service = ReRankerService()