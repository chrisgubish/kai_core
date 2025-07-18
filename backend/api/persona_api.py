# persona_api.py
"""FastAPI service for multi‑persona emotional AI (Eden & Kai).

This is a **drop‑in replacement** for the old `eden_api.py`.
Key differences:
• Supports an arbitrary number of personas via PERSONAS dict.
• Each persona supplies its own `build_prompt()` helper so the
  core pipeline never touches big system‑prompt strings.
• Single /chat endpoint — client passes { "persona": "kai" } or
  omits the field to default to Eden.
• Memory, abuse filters, affect engine, scheduler all stay shared.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Imports – (unchanged from your previous file, but grouped logically)
# ---------------------------------------------------------------------------
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path

from collections import defaultdict

from threading import Thread
from typing import List, Dict, Callable
import os, re, torch

from dotenv import load_dotenv

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    pipeline,
    BitsAndBytesConfig,
)

from backend.inference.affect import Affect_State
from backend.memory.memory_store import Memory_Store
from .emotion_weights import get_emotion_weights
from .tone_adapter import friendify, force_casual, is_formal_essay
from backend.persona.scheduler import run_scheduler, stop_scheduler

from backend.memory.eden_memory_defender import (
    is_sexualized_prompt,
    is_racist_prompt,
    is_troll_prompt,
    is_shock_prompt,
)

#  Persona builders (separate modules)
from backend.persona.kai_persona import build_prompt as build_kai_prompt
from backend.persona.eden_persona import build_prompt as build_eden_prompt  # you will extract Eden here

# ---------------------------------------------------------------------------
# Environment + FastAPI init
# ---------------------------------------------------------------------------
load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")

#creates FastAPI app object instance
app = FastAPI()

#enables Cross-Origin Resource Sharing so frontend can talk with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#base directory in relation to current API path location, formated this way
#due to moving file around for various purposes (encryption, future dev accessability, etc.)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = BASE_DIR / "frontend" / "static"

#app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------

#pulls Affect_State and Memory_Store classes and creates class instances in API
#Instantiates AffectState to enables emotional and trust tracking across sessions
affect = Affect_State()
#Instantiates MemoryStore creates conversational memory
memory_store = Memory_Store()

# ---------------------------------------------------------------------------
# Model & tokenizer – unchanged
# ---------------------------------------------------------------------------
MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.2"

#allows for 4-bit quantization through BitsAndBytesConfig to allow for faster inference and
#reduces memory usage, avoids overloading VRAM and crashing GPU
quant_cfg = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16)

#device_map="auto" automatically distributes/splits up usage between the GPU and CPU for the user
_tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, token=HF_TOKEN)
_model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    device_map="auto",
    quantization_config=quant_cfg,
    token=HF_TOKEN,
)

#creates pipeline to model, tokenizes user input, feeds tokens to model, generates a response
_generator = pipeline(
    "text-generation",
    model=_model,
    tokenizer=_tokenizer,
    torch_dtype=torch.float16,
)

# ---------------------------------------------------------------------------
# Persona registry – add new voices here
# ---------------------------------------------------------------------------
PersonaConfig = Dict[str, str | Callable]

#pulls files for eden's and kai's personality and registers persona configs
#Eden - motherlike figure guiding/monitoring Kai and allows the user to have access to a more 
#maternal figure
#Kai - fun, warm companion that feels like a friend sitting on your couch
PERSONAS: Dict[str, PersonaConfig] = {
    "eden": {
        "builder": build_eden_prompt,
        "speaker": "eden",
        "default_tone": "calm",
        "temperature": 0.72,
    },
    "kai": {
        "builder": build_kai_prompt,
        "speaker": "kai",
        "default_tone": "soft",
        "temperature": 0.85,
    },
}

DEFAULT_SESSION = "default"

# ---------------------------------------------------------------------------
# Pydantic request model
# ---------------------------------------------------------------------------
#creates class and functions for user_input, session_id, and persona based on
#user's interaction 
class ChatRequest(BaseModel):
    user_input: str
    session_id: str | None = DEFAULT_SESSION
    persona: str | None = "eden"  # "eden" or "kai" (default Eden)

# ---------------------------------------------------------------------------
# Helper – build prompt with persona history injection
# ---------------------------------------------------------------------------

#builds short transcript of user's message history, feeds it to persona, attaches latest user message
#and creates a prompt/message history that can easily be fed to the LLM
def _assemble_prompt(builder: Callable[[str, str], str], user_msg: str, history: list[dict]) -> str:
    """Format recent messages and delegate to builder."""
    history_block = "".join(
        f"You: {m['message']}\n" if m["speaker"] == "user" else f"{m['speaker'].capitalize()}: {m['message']}\n"
        for m in history
    )
    return builder(user_message=user_msg, history_block=history_block.strip())

# ---------------------------------------------------------------------------
# /chat endpoint – persona aware
# ---------------------------------------------------------------------------

#POST route for chat endpoint
@app.post("/chat")
async def chat(req: ChatRequest):
    persona_key = (req.persona or "eden").lower()

    #load persona config
    cfg = PERSONAS.get(persona_key)
    if cfg is None:
        return {"error": f"Unknown persona: {persona_key}"}
    build_prompt: Callable[[str, str], str] = cfg["builder"]  # type: ignore
    speaker: str = cfg["speaker"]  # eden | kai
    tone_default: str = cfg["default_tone"]
    temp: float = cfg["temperature"]
    
    #Assign session ids or uses default if none selected
    session = req.session_id or DEFAULT_SESSION
    #strips any accidental Eden or Kai prefixes in user message, feels more natural
    user_msg = re.sub(r"^(Eden|Kai):", "", req.user_input.strip()).strip()
    if not user_msg:
        return {"error": "Empty input"}

    # --- Safety / abuse filters (shared) ------------------------------------
    if is_sexualized_prompt(user_msg):
        count = memory_store.count_tag("flag:sexualized", session)
        if count >= 2:
            reply = "This is not the space for that. Continued misuse may result in a locked session."
            reply_tone = "firm"
        else:
            reply = (
                "I’m sensing the conversation is moving toward intimacy. "
                "I’m here to support emotional well‑being, not explicit content. "
                "Maybe we can explore what’s underneath those feelings?"
            )
            reply_tone = "calm"

        memory_store.save("user", user_msg, "inappropriate", ["flag:sexualized"], session_id=session)
        memory_store.save(speaker, reply, reply_tone, ["response", "deflected"], session_id=session)
        return {"response": reply, "emotions": {}}

    # --- Affect & emotion tagging ------------------------------------------
    affect.update(user_msg, session_id=session, persona=persona_key)
    trust_score = affect.get_vector(session_id=session, persona=persona_key).get("trust", 0)
    emotion_scores = get_emotion_weights(user_msg)
    emotion_tags = [f"emotion:{e}:{s}" for e, s in emotion_scores.items()]

    # --- History -----------------------------------------------------------
    history = memory_store.get_recent(limit=6, session_id=session)
    prompt = _assemble_prompt(build_prompt, user_msg, history)

    # --- Language generation ----------------------------------------------
    try:
        raw = _generator(
            prompt,
            max_new_tokens=200,
            temperature=temp,
            top_p=0.92,
            repetition_penalty=1.1,
            do_sample=True,
        )[0]["generated_text"]

        # Extract reply after the last persona cue (simple heuristic)
        reply = re.split(r"(Eden:|Kai:|You:|<\|assistant\|>)", raw)[-1].strip()

        # Tone adaptation if reply too formal
        if is_formal_essay(reply):
            softened = friendify(reply)
            reply = softened or reply
        reply = force_casual(reply)

        # Strip robotic disclaimers
        if re.search(r"^I\s*(am|\'m) (just|an) AI", reply, re.I):
            reply = "I’m here, really here. And I’m listening. What’s on your heart?"

    except Exception as exc:
        return {"error": str(exc)}

    if not reply:
        return {"error": "Final reply was empty."}

    # --- Persist convo -----------------------------------------------------
    memory_store.save("user", user_msg, "unknown", ["input", *emotion_tags], session_id=session)
    memory_store.save(speaker, reply, tone_default, ["response"], session_id=session)

    return {"response": reply, "emotions": emotion_scores}

# ---------------------------------------------------------------------------
# Misc endpoints (unchanged, updated speaker where needed)
# ---------------------------------------------------------------------------
@app.get("/chat.html")
async def serve_chat_html():
    return FileResponse(BASE_DIR / "frontend" / "chat.html")

@app.get("/")
def root():
    return RedirectResponse(url="/static/chat.html")

@app.get("/memory")
async def get_memory(session: str = DEFAULT_SESSION):
    return memory_store.get_recent(10, session_id=session)

@app.get("/memory/reset")
async def reset_memory(session: str = DEFAULT_SESSION):
    memory_store.clear(session)
    return {"status": f"Memory for session '{session}' cleared."}

@app.get("/memory/reset_all")
async def reset_all_memory():
    memory_store.clear_all()
    return {"status": "All memory cleared."}

@app.get("/sessions", response_model=List[str])
def list_sessions():
    return list(memory_store.sessions.keys())

@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    memory_store.clear(session_id)
    return {"message": f"Session '{session_id}' cleared."}

@app.delete("/sessions")
def delete_all_sessions():
    memory_store.clear_all()
    return {"message": "All sessions cleared."}

@app.post("/clear_session")
async def clear_session(request: Request):
    data = await request.json()
    session_id = data.get("session_id", DEFAULT_SESSION)
    memory_store.clear(session_id)
    return {"status": f"Session '{session_id}' cleared."}

# ---------------------------------------------------------------------------
# Scheduler hooks (unchanged)
# ---------------------------------------------------------------------------
scheduler_thread = None

@app.on_event("startup")
async def startup_event():
    global scheduler_thread
    scheduler_thread = Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("[FastAPI] Scheduler launched.")

@app.on_event("shutdown")
async def shutdown_event():
    stop_scheduler()
    print("[FastAPI] Scheduler stopped.")

# ---------------------------------------------------------------------------
# Dream log endpoint (unchanged)
# ---------------------------------------------------------------------------
@app.get("/dreamlog")
async def get_dreamlog(n: int = 5):
    try:
        from backend.persona.eden_monologue import get_recent_monologues
        logs = get_recent_monologues(n)
        return {"logs": logs}
    except Exception as e:
        return {"error": str(e)}
