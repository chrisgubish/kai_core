from __future__ import annotations

from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import json

MEMORY_FILE = Path("eden_memory.json")

class Memory_Store:
    # ----------------------------------------------------
    # ctor / bootstrap
    # ----------------------------------------------------
    def __init__(self) -> None:
        self.sessions: dict[str, List[dict]] = defaultdict(list)
        if MEMORY_FILE.exists():
            self._load()

    # ----------------------------------------------------
    # core persistence helpers
    # ----------------------------------------------------
    def _persist(self) -> None:
        with MEMORY_FILE.open("w", encoding="utf-8") as f:
            json.dump(self.sessions, f, indent=2)

    def _load(self) -> None:
        with MEMORY_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            self.sessions = defaultdict(list, {"default": data})
        else:
            self.sessions = defaultdict(list, {k: v for k, v in data.items()})

    # ----------------------------------------------------
    # public API
    # ----------------------------------------------------
    def save(
        self,
        speaker: str,
        message: str,
        emotion: str = "neutral",
        tags: Optional[list[str]] = None,
        session_id: str = "default",
    ) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
            "speaker": speaker,
            "message": message,
            "emotion": emotion,
            "tags": tags or [],
        }
        self.sessions[session_id].append(entry)
        self._persist()

    def get_recent(
        self,
        limit: int = 10,
        session_id: str = "default",
        speaker: Optional[str] = None,
        tag_filter: Optional[list[str]] = None,
    ) -> List[dict]:
        records = self.sessions.get(session_id, [])
        out: list[dict] = []

        for entry in reversed(records):
            if speaker and entry["speaker"] != speaker:
                continue
            if tag_filter and not any(t in entry["tags"] for t in tag_filter):
                continue
            out.append(entry)
            if len(out) == limit:
                break
        return list(reversed(out))

    def tag_counts(self, session_id: str = "default") -> dict[str, int]:
        counts: Counter[str] = Counter()
        for entry in self.sessions.get(session_id, []):
            counts.update(entry.get("tags", []))
        return dict(counts)

    def count_tag(self, tag: str, session_id: str = "default") -> int:
        return sum(tag in entry.get("tags", []) for entry in self.sessions.get(session_id, []))

    def clear(self, session_id: str = "default") -> None:
        self.sessions[session_id] = []
        self._persist()

    def clear_all(self) -> None:
        self.sessions.clear()
        self._persist()

    def get_trust_history(self, session_id: str = "default", speaker: Optional[str] = None) -> List[tuple[str, float]]:
        history = []
        for entry in self.sessions.get(session_id, []):
            if speaker and entry.get("speaker") != speaker:
                continue
            for tag in entry.get("tags", []):
                if tag.startswith("affect:trust:"):
                    parts = tag.split(":")
                    try:
                        if len(parts) == 4:
                            score = float(parts[-1])
                            history.append((entry["timestamp"], score))
                    except ValueError:
                        continue
        return history

    def save_affect_score(self, persona: str, trust_score: float, session_id: str = "default") -> None:
        trust_tag = f"affect:trust:{persona}:{trust_score:.2f}"
        self.save(
            speaker=persona,
            message=f"[affect-trust-update] {trust_score:.2f}",
            emotion="neutral",
            tags=[trust_tag],
            session_id=session_id,
        )
