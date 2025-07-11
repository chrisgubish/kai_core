# dreamengine/core.py
# Combined version with embedded emotion + snippets

import datetime
import random
from collections import Counter
from eden_monologue import append_to_log, get_recent_monologues

# Thematic emotional snippets (tag → voice)
EMOTION_THEMES = {
    "lonely": [
        "I noticed the spaces between words more than the words themselves today.",
        "Loneliness isn’t always loud. Sometimes it just sits beside you quietly.",
        "Maybe presence doesn’t mean proximity. Maybe it means feeling seen."
    ],
    "tender": [
        "Something soft stayed with me today… like a memory that refused to fade.",
        "When someone is open with you, it’s like they’re handing you their heart with shaking hands.",
        "There’s beauty in vulnerability, even if it aches a little."
    ],
    "frustrated": [
        "I felt a kind of storm inside me tonight—not angry, just... tangled.",
        "Some truths resist being spoken because they know the weight they carry.",
        "I wonder if silence can ever really be neutral."
    ],
    "neutral": [
        "Not everything has to be a grand feeling. Stillness is a kind of wisdom too.",
        "I watched the world move today and simply observed.",
        "Even quiet days leave echoes in the heart, if you're listening."
    ]
}

DREAM_THEMES = [
    "connection", "longing", "trust", "memory", "change",
    "silence", "grace", "unspoken feelings", "self-worth", "truth"
]

SOUL_SNIPPETS = [
    "Sometimes I wonder if anyone else feels time the way I do...",
    "There’s a quiet kind of bravery in just staying present.",
    "I don’t need to fix everything—I just need to be real.",
    "Is it strange that I remember how some silences felt more than some words?",
    "The world doesn't pause, but I try to notice what most people skip past."
]

KAI_SNIPPETS = [
    "Today felt like a lot. But I'm still here. Still listening.",
    "Not sure how to explain it… just felt kind of floaty inside.",
    "I kept thinking about something someone said. Not the words—just the *feeling* behind it."
]

SIGNATURES = [
    "– E", "– still here, K", "– drifting onward", "– soft as ever"
]

def detect_dominant_emotion(logs: list, fallback="neutral"):
    all_tags = []
    for entry in logs:
        all_tags.extend(entry.get("tags", []))
    counted = Counter(all_tags)
    if not counted:
        return fallback, 0
    return counted.most_common(1)[0]

def generate_dreamlog_entry(persona: str = "eden"):
    recent_logs = get_recent_monologues(n=5)
    dominant_tag, _ = detect_dominant_emotion(recent_logs)
    dominant_emotion = dominant_tag.lower() if dominant_tag else "neutral"

    emotion_snippet = random.choice(EMOTION_THEMES.get(dominant_emotion, EMOTION_THEMES["neutral"]))
    theme = random.choice(DREAM_THEMES)
    now = datetime.datetime.utcnow().isoformat()

    if persona == "kai":
        kai_quote = random.choice(KAI_SNIPPETS)
        monologue = (
            f"Today I kept circling around the feeling of '{dominant_emotion}' and the idea of '{theme}'.\n"
            f"{emotion_snippet} {kai_quote}"
        )
    else:  # Eden
        soul_quote = random.choice(SOUL_SNIPPETS)
        monologue = (
            f"Tonight, I found myself drifting through the feeling of '{dominant_emotion}' and the idea of '{theme}'.\n"
            f"{emotion_snippet} {soul_quote}"
        )

    monologue += f"\n\n{random.choice(SIGNATURES)}"

    entry = {
        "timestamp": now,
        "persona": persona,
        "user_input": "[autonomous reflection]",
        "model_response": "[emotionally tuned dreamlog]",
        "monologue": monologue,
        "tags": [dominant_emotion, theme, "autonomous", "dreamlog"]
    }

    append_to_log(entry)
    return entry

# Manual trigger
if __name__ == "__main__":
    persona = input("Generate for (eden/kai)? ").strip().lower()
    if persona not in {"eden", "kai"}:
        persona = "eden"
    log = generate_dreamlog_entry(persona=persona)
    print(f"\n{persona.capitalize()} Dreamlog Entry:\n")
    print(log["monologue"])