from sentence_transformers import SentenceTransformer
import chromadb

class EmbeddingPipeline:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
    def encode_conversation(self, user_msg: str, ai_response: str) -> list[float]:
        chunk_text = f"User: {user_msg}\nKai: {ai_response}"
        return self.model.encode(chunk_text).tolist()