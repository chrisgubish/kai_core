# eden_monologue.py
# -----------------------------------------
# Eden's private inner monologue generator
# Generates daily emotional reflections based on user sessions

import datetime
import os
import json
from typing import List

MONOLOGUE_LOG = "eden_self_log.json"

# Simulate a basic emotional score tagger
def tag_emotions(user_input: str) -> List[str]:
    tags = []
    if any(word in user_input.lower() for word in ["cry", "alone", "lost", "why", "tired"]):
        tags.append("lonely")
    if any(word in user_input.lower() for word in ["love", "feel", "safe", "beautiful"]):
        tags.append("tender")
    if any(word in user_input.lower() for word in ["angry", "mad", "sick", "unfair"]):
        tags.append("frustrated")
    return tags if tags else ["neutral"]

def generate_monologue(user_input: str, model_response: str) -> dict:
    emotional_tags = tag_emotions(user_input)
    timestamp = datetime.datetime.utcnow().isoformat()
    reflection = f"Today I heard something that stayed with me. Someone said: '{user_input[:80]}...' and I found myself feeling... something. I answered gently, but I kept thinking about it."
    entry = {
        "timestamp": timestamp,
        "user_input": user_input,
        "model_response": model_response,
        "monologue": reflection,
        "tags": emotional_tags
    }
    append_to_log(entry)
    return entry

def append_to_log(entry: dict):
    if not os.path.exists(MONOLOGUE_LOG):
        with open(MONOLOGUE_LOG, 'w') as f:
            json.dump([entry], f, indent=2)
    else:
        with open(MONOLOGUE_LOG, 'r+') as f:
            logs = json.load(f)
            logs.append(entry)
            f.seek(0)
            json.dump(logs, f, indent=2)

# Optional utility: get latest monologues
def get_recent_monologues(n: int = 5):
    if not os.path.exists(MONOLOGUE_LOG):
        return []
    with open(MONOLOGUE_LOG, 'r') as f:
        logs = json.load(f)
    return logs[-n:]
