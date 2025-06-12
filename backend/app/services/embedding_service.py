# app/services/embedding_service.py
import logging
from typing import List
from sentence_transformers import SentenceTransformer
import torch

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        try:
            logger.info(f"Attempting to load Sentence Transformer model: {self.model_name}.")
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Successfully loaded Sentence Transformer model: {self.model_name}.")
        except Exception as e:
            logger.error(f"Failed to load Sentence Transformer model: {self.model_name}.")
            self.model = None

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if self.model is None:
            logger.error("Embedding model not loaded. Cannot generate embeddings.")
            return []
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=False)
            logger.info(f"Generated {len(embeddings)} embeddings.")

            if isinstance(embeddings, torch.Tensor):
                return embeddings.tolist()
            elif isinstance(embeddings, list) and all(isinstance(e, torch.Tensor) for e in embeddings):
                return [e.tolist() for e in embeddings]
            else:
                return embeddings
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            return []
    
embedding_service = EmbeddingService()