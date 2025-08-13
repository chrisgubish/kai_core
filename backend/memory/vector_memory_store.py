from .embeddings import EmbeddingPipeline
import chromadb
from datetime import datetime
from typing import List, Dict

class VectorMemoryStore:
    def __init__(self):
        self.embedding_pipeline = EmbeddingPipeline()
        self.client = chromadb.Client()
        self.collection = self.client.create_collection(
            name="conversations",
            metadata={"hnsw:space": "cosine"}
        )

    def save_interaction(self, user_msg: str, ai_response: str, emotional_data: dict, session_id: str):
        #Generate embedding
        embedding = self.embedding_pipeline.encode_conversation(user_msg, ai_response)

        #Store in vector DB
        self.collection.add(
            documents=[F"User: {user_msg}\nAI: {ai_response}"],
            embeddings=[embedding],
            metadatas=[{
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "emotions":str(emotional_data)
            }],
            ids=[f"{session_id}_{datetime.now().timestamp()}"]
        )

    def get_contextual_memory(self, query: str, session_id: str, limit: int = 3) -> List[dict]:
        return [] #Placeholder implementation