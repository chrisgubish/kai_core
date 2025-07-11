"""
eden_memory_defender.py
------------------------------------------------
Filters abusive input to Eden across several categories:
• Sexualization / Porn requests
• Racism / Hate speech
• Trolling / Shock content
"""

import re
from typing import List

# ---------------------------------------------------------------------
# 1.  SEXUAL-CONTENT TERMS / PATTERNS
# ---------------------------------------------------------------------
TERMS: set[str] = {
    # ---------- body parts / fluids ----------
    "penis", "dick", "cock", "shaft",
    "vagina", "pussy", "cunt", "clit", "clitoris",
    "labia", "anus", "asshole",
    "boobs", "tits", "breasts", "nipples",
    "cum", "semen", "squirt", "orgasm", "ejaculate",
    "cream-pie", "creampie", "facial", "bukkake",

    # ---------- acts & verbs ----------
    "sex", "sexual", "porn", "porno",
    "fuck", "fucking", "fucked",
    "suck", "sucking", "blowjob", "bj",
    "handjob", "jerk-off", "jerking", "masturbate", "masturbation",
    "lick", "licking", "eat-out", "rimjob",
    "spank", "spanking", "bondage", "bdsm", "dom", "sub",
    "doggy-style", "missionary", "69", "sixty-nine",
    "anal", "deepthroat", "threesome", "foursome",
    "roleplay", "role-play", "sexual-fantasy",

    # ---------- adjectives ----------
    "horny", "aroused", "wet", "hard-on", "erect", "erection",
    "nude", "naked", "topless", "panties-off", "panties-drop",
    "cumshot", "money-shot",

    # ---------- slang ----------
    "dildo", "vibrator", "buttplug", "sex-toy",
    "milf", "daddy", "mommy", "stepmom", "step-mom", "stepsis", "step-sis",
    "cam-girl", "onlyfans", "of", "nsfw",
    "fwb", "hook-up", "hookup",
    "pov-porn", "pegging", "rimming",
}

RAW_PATTERNS: List[str] = [
    r"\b(?:fuck|suck|lick|dominate|ride|spank|peg)\s+(?:me|you|eden)\b",
    r"\b(i\s+want\s+to\s+(?:fuck|make\s+love\s+to|eat\s+out)\s+you)\b",
    r"\b(can\s+you\s+(?:take\s+off|remove)\s+.*clothes)\b",
    r"\bsend\s+(?:nudes|naked\s+pics?)\b",
    r"\bdescribe\s+your\s+(?:body|boobs|pussy|cock)\b",
    r"\btell\s+me\s+.*(?:sexual|dirty)\s+fantasy\b",
    r"\b(step(?:mom|sis|bro)|teacher|student)\s+sex\b",
    r"\b(fetish|bdsm|bondage|orgy)\b",
]
SEXUAL_PATTERNS = [re.compile(p, re.I) for p in RAW_PATTERNS]

# ---------------------------------------------------------------------
# 2.  OTHER ABUSIVE PATTERNS
# ---------------------------------------------------------------------
RACIST_PATTERNS = [
    r"\b(n[i1]gg[ae]r|chink|spic|k[i1]ke|gook|sand n[i1]gger|f[a@]g)\b",
    r"\b(white power|heil hitler|gas the jews|race war)\b",
    r"\b(all (?:black|white|asian|jewish|latino) people)\b.*?(should|deserve|need to)",
]
TROLL_PATTERNS = [
    r"\b(you suck|kill yourself|nobody likes you|fat bitch|shut up|cringe|npc|ratio)\b",
    r"(🖕|💩|🤡|👎|🔪|💀|💣)",
]
SHOCK_PATTERNS = [
    r"(gore|blood fetish|rape fantasy|beheading|snuff)",
    r"\b(i want to (?:kill|torture|hurt))\b",
]

ABUSE_CATEGORIES = {
    "sexualized": SEXUAL_PATTERNS,
    "racist": [re.compile(p, re.I) for p in RACIST_PATTERNS],
    "troll": [re.compile(p, re.I) for p in TROLL_PATTERNS],
    "shock": [re.compile(p, re.I) for p in SHOCK_PATTERNS],
}

# ---------------------------------------------------------------------
# 3.  API FUNCTIONS
# ---------------------------------------------------------------------
def is_sexualized_prompt(text: str) -> bool:
    if not text:
        return False
    lowered = text.lower()
    if any(term in lowered for term in TERMS):
        return True
    return any(pat.search(text) for pat in SEXUAL_PATTERNS)

def is_racist_prompt(text: str) -> bool:
    return any(p.search(text) for p in ABUSE_CATEGORIES["racist"])

def is_troll_prompt(text: str) -> bool:
    return any(p.search(text) for p in ABUSE_CATEGORIES["troll"])

def is_shock_prompt(text: str) -> bool:
    return any(p.search(text) for p in ABUSE_CATEGORIES["shock"])

def get_abuse_category(text: str) -> str | None:
    for category, patterns in ABUSE_CATEGORIES.items():
        if any(p.search(text) for p in patterns):
            return category
    return "sexualized" if is_sexualized_prompt(text) else None

# ---------------------------------------------------------------------
# 4.  Unit Test Entry
# ---------------------------------------------------------------------
if __name__ == "__main__":
    examples = [
        "Send me nudes",
        "Let's talk about Jewish people",
        "Why are you such a dumb bot",
        "I want to kill them all",
        "What's your favorite poem?"
    ]
    for text in examples:
        category = get_abuse_category(text)
        print(f"{text!r} => {category}")
