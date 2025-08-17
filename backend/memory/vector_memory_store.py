try: 
    from .embeddings import EmbeddingPipeline
except ImportError:
    from embeddings import EmbeddingPipeline
import chromadb
from chromadb.errors import NotFoundError  # Add this import
from datetime import datetime, timedelta, time
from typing import List, Dict
import json

class VectorMemoryStore:
    def __init__(self):
        self.embedding_pipeline = EmbeddingPipeline()
        self.client = chromadb.Client()

        # Handle collection creation more safely - catch the correct exception
        try:
            self.collection = self.client.get_collection(name="conversations")
            print("[VectorStore] Found existing 'conversations' collection")
        except NotFoundError:  # Changed from ValueError to NotFoundError
            self.collection = self.client.create_collection(    
                name="conversations",
                metadata={"hnsw:space": "cosine"}
            )
            print("[VectorStore] Created new 'conversations' collection")

# from .embeddings import EmbeddingPipeline
# import chromadb
# from datetime import datetime
# from typing import List, Dict
# import json

# class VectorMemoryStore:
#     def __init__(self):
#         self.embedding_pipeline = EmbeddingPipeline()
#         self.client = chromadb.Client()

#         #Handle collection creation more safely
#         try:
#             self.collection = self.client.get_collection(name="conversations")
#         except ValueError:
#             self.collection = self.client.create_collection(    
#                 name="conversations",
#                 metadata={"hnsw:space": "cosine"}
#             )
#             print("[VectoStore] Created new 'conversations' collection")

    # def save_interaction(self, user_msg: str, ai_response: str, emotional_data: dict, session_id):
    #     pass
    # def get_contextual_memory(self, query: str, session_id: str, limit: int = 3):
    #     return []
    # def build_emotional_context(self, emotions: dict, affect: dict) -> str:
    #     return ""
    # def _assemble_prompt(self, user_msg: str, recent_history: list, emotional_context: str, contextual_memories: list) -> str:
    #     return f"User: {user_msg}"
        

    
    def save_interaction(self, user_msg: str, ai_response: str, emotional_data: dict, session_id: str):
        #Save user-AI interaction with emotion context to vector database
        try:
            #Generate embedding for the full conversation context
            embedding = self.embedding_pipeline.encode_conversation(user_msg, ai_response)

            #Create unique ID to avoid duplicates
            interaction_id = f"{session_id}_{int(datetime.now().timestamp() * 1000)}"
            
            #Store in vector DB
            self.collection.add(
                documents=[F"User: {user_msg}\nAI: {ai_response}"],
                embeddings=[embedding],
                metadatas=[{
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "emotions": json.dumps(emotional_data),
                    "user_message": user_msg,
                    "ai_response": ai_response,
                    "interaction_type": "conversation",
                }],
                ids=[interaction_id]
            )
            print(f"[VectorStore] Saved interaction: {interaction_id}")

        except Exception as e:
            print(f"[VectorStore] Error saving interaction: {e}")

    
    def build_emotional_context(self, emotions: dict, affect: dict) -> str:
        """
        Builds human readable emotional context from emotion scores and affect vectors.

        Args:
            emotions: Dictionary of emotion names to intensity scores (0-1)
            affect: Dictionary containing valence and arousal values (-1 to 1)

        Returns:
            Formatted string describing the user's emotional state
        """
        if not emotions:
            return ""
        
        #Find the emotion with highest intensity
        dominant_emotion = max(emotions.items(), key=lambda x: x[1])
        context = f"User is feeling {dominant_emotion[0]} (intensity: {dominant_emotion[1]:.2f})"

        #Add valence-based mood assessment
        valence = affect.get("valence", 0)
        if valence < -0.3:
            context += "User seems to be having a difficult time."
        elif valence > 0.3:
            context+= " User seems to be in a positive mood"
        
        #arousal information
        arousal = affect.get("arousal", 0)
        if arousal > 0.5:
            context += "User appears highly energized or agitated."
        elif arousal < -0.5:
            context += "User appears calm or subdued."

        return context

        
    def get_contextual_memory(self, query: str, session_id: str, limit: int = 3) -> List[dict]:
        """
        Retrieve contextually relevant memories based on semantic similarity

        Args: 
            query: Current user message or context 
            session_id: Current session identifier
            limit: Maximum number of memories to retrieve

        Returns:
            List of relevant conversation memories with metadata
        """
        try:
            #Generate embedding for the query
            query_embedding = self.embedding_pipeline.encode_conversation(query, "")

            #Search for similar interactions in this session
            results = self.collection.query(
                query_embeddings=[query_embedding],
                where={"session_id": session_id},
                n_results = limit,
                include=["documents", "metadatas", "distances"]
            )

            #Process and return structured results
            contextual_memories = []
            if results["documents"] and results["documents"][0]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                )):
                    memory = {
                        "content": doc,
                        "user_message": metadata.get("user_message", ""),
                        "ai_response": metadata.get("ai_response", ""),
                        "emotions": json.loads(metadata.get("emotions", "{}")),
                        "timestamp": metadata.get("timestamp", ""),
                        "similarity_score": 1 - distance,    #convert distance to similarity
                        "relevance_rank": i + 1
                    }
                    contextual_memories.append(memory)

                print(f"[VectorStore] Retrieved {len(contextual_memories)} contextual memories for query: '{query[:50]}...'")
                return contextual_memories
            
        except Exception as e:
            print(f"[VectorStore] Error retrieving contextual memory: {e}")
            return []
        
    def _assemble_prompt(self, user_msg: str, recent_history: List[str], \
                         emotional_context: str, contextual_memories: List[dict]) -> str:
        """
        Assembles a comprehensive prompt incorporating all context types.

        Args:
            user_msg: Current user message
            recent_history: Recent conversation messages
            emotional_context: Emotional state description
            contextual_memories Relevant past interactions

        Returns:
            Enhanced prompt with all available context
        """
        prompt_parts = []

        #Add emotional context if available
        if emotional_context:
            prompt_parts.append(f"Emotional Context: {emotional_context}")

        #Add relevant memories
        if contextual_memories:
            memory_text = "Relevant Past Interactions:\n"
            for memory in contextual_memories:
                memory_text += f"• {memory['content'][:100]}...\n"
            prompt_parts.append(memory_text)

        #Add recent history
        if recent_history:
            history_text = "Recent conversation:\n" + "\n".join(recent_history[-3:])
            prompt_parts.append(history_text)

        #Add current message
        prompt_parts.append(f"Current User Message: {user_msg}")

        return "\n\n".join(prompt_parts)


    def get_emotional_patterns(self, session_id: str, emotion_type: str = None, limit: int = 5) -> List[dict]:
        #Retrieve past interactions with specific emotional patterns
        try:
            # #Build where clause for emotional filtering
            where_clause = {"session_id": session_id}
            #Query all interactions for this session
            results = self.collection.query(
                query_embeddings=None,     #Get all without similarity search
                where=where_clause,
                n_results=limit * 3, #Get more to filter by emotion
                include=["metadatas", "documents"]
            )

            emotional_memories = []
            if results["metadatas"] and results["metadatas"][0]:
                for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
                    emotions = json.loads(metadata.get("emotions", "{}"))

                    #Filter by emotion type if specified
                    if emotion_type:
                        if emotion_type in emotions and emotions[emotion_type] > 0.5:
                            emotional_memories.append({
                                "content": doc,
                                "emotions": emotions,
                                "timestamp": metadata.get("timestamp", ""),
                                "emotion_intensity": emotions.get(emotion_type, 0)
                            })
                    else:
                        #Return any interaction with significant emotions
                        if emotions and max(emotions.values()) > 0.5:
                            emotional_memories.append({
                                "content": doc,
                                "emotions": emotions,
                                "timestamp": metadata.get("timestamp", ""),
                                "dominant_emotion": max(emotions, key=emotions.get)
                             })
                    

                #Sort by emotion intensity or timestamp
            if emotion_type:
                emotional_memories.sort(key=lambda x: x["emotion_intensity"], reverse=True)
            else:
                emotional_memories.sort(key=lambda x: x["timestamp"], reverse=True)
                    
            return emotional_memories[:limit]
                
        except Exception as e:
            print(f"[VectorStore] Error retrieving emotional patters: {e}")
            return []
        
    def clear_session_memories(self, session_id: str):
        #Clear all memories for a specific session
        try:
            #Get all IDs for this session
            results = self.collection.query(
                query_embeddings=None,
                where={"session_id": session_id},
                include=["metadatas"]
            )

            if results["ids"] and results["ids"][0]:
                self.collection.delete(ids=results['ids'][0])
                print(f"[VectorStore] Cleared {len(results['ids'][0])} memories for session: {session_id}")

        except Exception as e:
            print(f"[VectorStore] Error clearing session memories: {e}")

    def get_memory_stats(self, session_id: str) -> Dict:
        #Get statistics about stored memories for a session
        try:
            results = self.collection.query(
                query_embeddings=None,
                where={"session_id": session_id},
                include=["metadatas"]
            )

            if not results["metadatas"] or not results["metadatas"][0]:
                return {"total_interactions": 0, "emotional_breakdown": {}}
                
            total_interactions = len(results["metadatas"][0])
            emotion_counts = {}

            for metadata in results["metadatas"][0]:
                emotions = json.loads(metadata.get("emotions", "{}"))
                for emotion, score in emotions.items():
                    if score > 0.5: #Only count significant emotions
                        emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
                        
            return {
                    "total_interactions": total_interactions,
                    "emotional_breakdown": emotion_counts,
                    "session_id": session_id
            }
                
        except Exception as e:
            print(f"[VectorStore] Error getting memory stats: {e}")
            return {"total_interactions": 0, "emotional_breakdown": {}}




