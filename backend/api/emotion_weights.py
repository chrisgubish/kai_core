"""
These emotional weights were calculated by using the National Research Council for Canada (NRC) Valence-Arousal-Dominance
 (VAD) and Affective Norms for English Words (ANEW) as the base for intensity values and the categories were defined using
 Linguistic Inquiry and Word Count (LIWC) Emotion Dictionaries and NRC Emotion Lexicon - Mohammad & Turney (EmoLex) for 
 the emotional categories. Both were combined and assisted with OpenAI for a general weight/category baseline and will 
 be refined over time through individual effort and analysis. Additional studies and systems may be used over time as 
 well to create more accurate/authentic modeling
"""
EMOTION_KEYWORDS = {
    "sadness": {
        "sad": 0.6, "depressed": 0.9, "cry": 0.8, "tear": 0.7,
        "heartbroken": 0.9, "grief": 0.9, "hurt": 0.7, "aching": 0.7,
    },
    "loneliness": {
        "lonely": 0.9, "alone": 0.8, "isolated": 0.8,
        "ignored": 0.7, "abandoned": 0.9, "unseen": 0.7, "unloved": 0.8,
    },
    "anxiety": {
        "anxious": 0.8, "nervous": 0.6, "panic": 0.9, "worry": 0.6,
        "overwhelmed": 0.7, "stressed": 0.7, "uneasy": 0.5,
    },
    "emptiness": {
        "empty": 0.9, "numb": 0.8, "hollow": 0.9, "void": 0.7,
        "flat": 0.5, "disconnected": 0.7,
    },
    "anger": {
        "angry": 0.7, "mad": 0.6, "furious": 0.9, "rage": 0.9,
        "pissed": 0.8, "resentful": 0.7, "frustrated": 0.7,
    },
    "shame": {
        "ashamed": 0.9, "guilty": 0.8, "worthless": 0.9,
        "embarrassed": 0.6, "disgraced": 0.8, "humiliated": 0.9,
    },
    "fear": {
        "afraid": 0.7, "scared": 0.8, "terrified": 1.0,
        "fear": 0.6, "worried": 0.5, "hesitant": 0.4,
    },
    "joy": {
        "happy": 0.6, "joyful": 0.8, "grateful": 0.7,
        "smiling": 0.5, "laughing": 0.6, "peaceful": 0.7,
    },
    "hope": {
        "hopeful": 0.8, "relieved": 0.7, "encouraged": 0.6,
        "uplifted": 0.6, "believe": 0.5, "faith": 0.6,
    },
    "love": {
        "loved": 0.8, "cared": 0.6, "held": 0.7,
        "safe": 0.6, "cherished": 0.8, "connected": 0.7,
    },
    "confusion": {
        "confused": 0.7, "lost": 0.8, "unsure": 0.6,
        "disoriented": 0.7, "uncertain": 0.5, "foggy": 0.5,
    },
    "longing": {
        "miss": 0.7, "yearn": 0.8, "crave": 0.7,
        "aching for": 0.9, "wish": 0.6, "nostalgic": 0.6,
    },
}
def get_emotion_weights(text: str) -> dict:
    weights = {}
    text = text.lower()
    for emotion, keywords in EMOTION_KEYWORDS.items():
        score = 0
        for word, weight in keywords.items():
            if word in text:
                score = max(score, weight)
        if score > 0:
            weights[emotion] = round(score, 2)
    return weights
