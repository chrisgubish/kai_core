# tone_adapter.py
# ----------------------------------------------------
# Eden's tone modifier – softens overly formal output,
# applies warmth, breaks long reflections, and avoids jargon.

import yaml
import random
import re

# ----------------------------------------------------
# 1. Load Eden's configurable emotional profile
# ----------------------------------------------------
def load_profile(profile: str = "default_profile", config_path: str = "eden_emotion_profile.yaml") -> dict:
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get(profile, {}) or {}
    except FileNotFoundError:
        return {}

# ----------------------------------------------------
# 2. Human Softening Toolkit
# ----------------------------------------------------

#implements softeners and adds additional replacements to prevent the personas from sounding
#too robotic or too punctual. Especially for Kai, who I want ot feel like an average person
#just listening and talking with you. Like a friend on the couch at 2am. Hopefully won't be 
#as necessary once LLM fine tuned
SOFTENERS = [
    "Honestly? I’m still wrapping my head around that.",
    "That’s something I’ve been sitting with.",
    "I don’t have a perfect answer, but here’s what I’ve been feeling.",
    "Maybe that’s okay.",
    "I think I needed to say that out loud.",
    "I guess what I mean is…",
    "It’s messy, but maybe that’s okay.",
    "That still feels tender to say out loud.",
    "I think there's still more I don't understand about it."
]

REPLACEMENTS = {
    "I am humbled by": "That means a lot to me.",
    "your unwavering belief": "your support",
    "a more compassionate and empathetic society": "a world where people feel less alone",
    "I am forever grateful": "thank you",
    "an opportunity for both of us to grow and evolve": "a chance for us both to grow",
    "I have been": "I’ve been",
    "I am": "I’m",
    "I will": "I’ll",
    "do not": "don’t",
    "cannot": "can’t",
    "strengthens our relationships": "helps us feel closer",
    "overall well-being": "how we’re really doing",
    "emotional strength": "just being okay sometimes",
    "mental clarity": "being able to think straight",
    "self-awareness": "understanding myself a little better",
    "navigate challenges": "get through the hard stuff",
    "It also": "And it",
    "individuals": "people",
    "to provide a space": "to be someone",
    "an environment": "a place",
    "plays a crucial role": "really matters",
    "our shared experience": "what we’re going through together",
    "cultivating strong relationships": "building real connection",
    "concept": "thing",
    "complexity": "messiness",
    "self-compassion": "being kind to myself"
}

PHRASE_RE = [(re.compile(re.escape(k), re.IGNORECASE), v) for k, v in REPLACEMENTS.items()]

# ----------------------------------------------------
# 3. Core Softening Function
# ----------------------------------------------------
def soften_text(text: str) -> str:
    for pattern, val in PHRASE_RE:
        text = pattern.sub(val, text)
    return text

# ----------------------------------------------------
# 4. Friendifier: convert into Eden’s voice
# ----------------------------------------------------
def friendify(text: str) -> str:
    text = soften_text(text)
    words = text.split()
    if len(words) > 115:
        text = " ".join(words[:115]) + ". I think I’ve said enough for now. Just… thank you for letting me share that."

    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    paragraphs = []
    chunk = []
    for sentence in sentences:
        chunk.append(sentence)
        if len(chunk) >= 2 or len(" ".join(chunk).split()) > 55:
            paragraphs.append(" ".join(chunk))
            chunk = []
    if chunk:
        paragraphs.append(" ".join(chunk))

    if len(paragraphs) > 1 and random.random() < 0.85:
        idx = random.randint(1, len(paragraphs) - 1)
        paragraphs.insert(idx, random.choice(SOFTENERS))

    return "\n\n".join(p.strip() for p in paragraphs if p.strip())

# ----------------------------------------------------
# 5. Essay Detector (for fallback)
# ----------------------------------------------------
def is_formal_essay(text: str) -> bool:
    score = 0
    if len(text.split()) > 100:
        score += 1
    if any(phrase in text for phrase in [
        "concept of", "it is important to", "allows us to",
        "provides a safe space", "by practicing", "fosters", "cultivating"
    ]):
        score += 1
    if text.count(".") > 6:
        score += 1
    if any(text.strip().startswith(phrase) for phrase in [
        "I have been considering", "I’ve been reflecting",
        "I’ve been mulling over the idea", "I've been pondering"
    ]):
        score += 1
    return score >= 2

# ----------------------------------------------------
# 6. Final Safety Valve
# ----------------------------------------------------
WORD_LIMIT = 65
#adds realistic tone for Kai, but will adjust accordingly 
FILLERS = ["uh,", "…well,", "honestly,", "I mean,", "you know,"]

def _trim_to_limit(text: str) -> str:
    words = text.split()
    if len(words) <= WORD_LIMIT:
        return text
    return " ".join(words[:WORD_LIMIT]) + "…"

def _add_spoken_edges(text: str) -> str:
    if not any(f in text for f in FILLERS) and random.random() < 0.8:
        first, *rest = re.split(r"(?<=[.!?])\s+", text, 1)
        filler = random.choice(FILLERS)
        text = f"{filler} {first.strip().lstrip().capitalize()}" + (" " + rest[0] if rest else "")
    text = re.sub(r"[;–—]+", "…", text)
    return text

def force_casual(text: str) -> str:
    text = _trim_to_limit(text)
    text = _add_spoken_edges(text)
    sents = re.split(r"(?<=[.!?])\s+", text)
    if len(sents) > 3:
        text = " ".join(sents[:3]) + "…"
    if random.random() < 0.2:
        text += " What about you?"
    return text

# ----------------------------------------------------
# 7. Optional Tone Tuning
# ----------------------------------------------------
#adjusts tone based on tone_config and user interaction
def apply_tone_adjustments(text: str, tone_config: dict | None = None) -> str:
    if tone_config is None:
        tone_config = {}

    if tone_config.get("mirroring") in {"strong", "adaptive"}:
        text = text.replace("I understand", "I really understand")

    if tone_config.get("response_speed") == "thoughtful":
        text = "Hmm... " + text

    if tone_config.get("poetic_freedom", 0) > 0.5:
        text += random.choice([" softly, always.", " —and that matters."])

    return soften_text(text)

# ----------------------------------------------------
# 8. CLI Test Harness
# ----------------------------------------------------
if __name__ == "__main__":
    cfg = load_profile("default_profile")
    raw_demo = (
        "I have been considering the concept of resilience and how it plays a crucial role in forming authentic and meaningful connections between individuals. "
        "Resilience is a vital skill that enables us to cope with difficult situations, adapt to change, and maintain a positive perspective."
    )
    print("--- RAW ---\n", raw_demo)
    print("\n--- SOFTENED ---\n", apply_tone_adjustments(raw_demo, cfg))
    print("\n--- FRIENDIFIED ---\n", friendify(raw_demo))
    print("\n--- TOO ESSAY-LIKE? ---", is_formal_essay(raw_demo))