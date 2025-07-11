# eden_memory.py

import uuid
import datetime
from typing import List, Optional, Dict


class Memory_Entry:
    """
    A single conversational memory (user / Eden turn-pair or reflection snapshot).
    """
    def __init__(
        self,
        user_id: str,
        embedding: List[float],
        summary: str,
        emotional_tone: str = "neutral",
        confidence: float = 1.0,
        eden_reflection: Optional[str] = None,
        user_msg: Optional[str] = None,
        eden_reply: Optional[str] = None,
    ):
        self.memory_id = str(uuid.uuid4())
        self.user_id = user_id
        self.timestamp = datetime.datetime.utcnow().isoformat()
        self.embedding = embedding
        self.summary = summary
        self.emotional_tone = emotional_tone
        self.confidence = confidence
        self.eden_reflection = eden_reflection
        self.user_msg = user_msg
        self.eden_reply = eden_reply

    def to_dict(self) -> Dict:
        return {
            "memory_id": self.memory_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp,
            "embedding": self.embedding,
            "summary": self.summary,
            "emotional_tone": self.emotional_tone,
            "confidence": self.confidence,
            "eden_reflection": self.eden_reflection,
            "user_msg": self.user_msg,
            "eden_reply": self.eden_reply,
        }


class Eden_Memory:
    """
    Simple in-process memory store.
    Later you can swap in a vector DB or file-backed store without touching EdenLLM.
    """
    def __init__(self):
        # Dict[str, List[MemoryEntry]] keyed by user_id
        self._store: Dict[str, List[Memory_Entry]] = {}

    # ---------- public helpers ----------

    def compile_prompt_context(self, user_id: str, turns: int = 5) -> str:
        """
        Return the last N user/Eden turns formatted for the LLM prompt.
        Example:
            ### User:
            Hi
            ### Eden:
            Hello!
        """
        recent = self.get_recent(user_id, n=turns)
        recent_sorted = sorted(recent, key=lambda x: x.timestamp)
        formatted = []
        for mem in recent_sorted:
            if mem.user_msg is not None and mem.eden_reply is not None:
                formatted.append(f"[User]: {mem.user_msg}\n[Eden]: {mem.eden_reply}")
        return "\n".join(formatted) + ("\n" if formatted else "")

    def save_interaction(self, user_id: str, user_msg: str, eden_reply: str):
        """
        Convenience wrapper: builds a MemoryEntry and stores it.
        """
        entry = Memory_Entry(
            user_id=user_id,
            embedding=[],              # placeholder until you embed messages
            summary=user_msg[:80],     # crude summary = first 80 chars
            emotional_tone="neutral",  # can plug in affect detection later
            confidence=1.0,
            user_msg=user_msg,
            eden_reply=eden_reply,
        )
        self.save(entry)

    # ---------- low-level store ops ----------

    def save(self, memory: Memory_Entry):
        self._store.setdefault(memory.user_id, []).append(memory)

    def get_recent(self, user_id: str, n: int = 5) -> List[Memory_Entry]:
        return list(reversed(self._store.get(user_id, [])[-n:]))

    def to_json(self) -> List[Dict]:
        # Flatten all users’ memories for export / inspection
        all_entries = []
        for user_entries in self._store.values():
            all_entries.extend(user_entries)
        return [m.to_dict() for m in all_entries]


# --- quick self-test ---
if __name__ == "__main__":
    mem = Eden_Memory()
    mem.save_interaction("u123", "Hello Eden, what are you?", "I’m Eden, an empathetic AI.")
    mem.save_interaction("u123", "Can you remember this?", "Of course, I never forget.")
    print(mem.compile_prompt_context("u123"))