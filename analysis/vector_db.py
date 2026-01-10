import os
import logging
from typing import List, Optional, Dict
from qdrant_client import QdrantClient
from qdrant_client.http import models
from langchain_ollama import OllamaEmbeddings

logger = logging.getLogger(__name__)

class VectorDBService:
    def __init__(self):
        self.qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
        self.collection_name = "course_tasks"
        self.client = QdrantClient(url=self.qdrant_url)
        
        # Configure Ollama Embeddings
        # We strip /v1 because langchain_ollama expects the base ollama URL
        base_url = os.getenv("AI_BASE_URL", "http://ollama:11434").replace("/v1", "")
        self.embedding_model = "nomic-embed-text-v2-moe"
        
        self.embeddings = OllamaEmbeddings(
            base_url=base_url,
            model=self.embedding_model
        )
        # nomic-embed-text-v2-moe supports Matryoshka learning, but defaults to 768
        self.vector_size = 768 

        self._ensure_collection()

    def _ensure_collection(self):
        try:
            collections = self.client.get_collections()
            exists = any(c.name == self.collection_name for c in collections.collections)
            
            if not exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.vector_size,
                        distance=models.Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}")

    def search_tasks(self, query_text: str, threshold: float = 0.85) -> List[Dict]:
        """
        Search for existing tasks semantically similar to query_text.
        """
        try:
            query_vector = self.embeddings.embed_query(query_text)
            
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=3,
                score_threshold=threshold
            )
            
            return [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload
                }
                for hit in search_result
            ]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def upsert_task(self, task_id: str, text: str, payload: Dict):
        """
        Insert or update a task vector.
        """
        try:
            vector = self.embeddings.embed_query(text)
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=task_id, 
                        vector=vector,
                        payload=payload
                    )
                ]
            )
            logger.info(f"Upserted task {task_id} to Qdrant")
        except Exception as e:
            logger.error(f"Upsert failed: {e}")
