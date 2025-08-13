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

from backend.memory.embeddings import EmbeddingPipeline
import chromadb

from collections import defaultdict

from threading import Thread
from typing import List, Dict, Callable, Optional
import os, re, torch
from datetime import datetime

from dotenv import load_dotenv

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    pipeline,
    BitsAndBytesConfig,
)

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from backend.inference.affect import Affect_State
from backend.memory.memory_store import Memory_Store
from backend.memory.vector_memory_store import VectorMemoryStore
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
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
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
# #Instantiates MemoryStore creates conversational memory
memory_store = Memory_Store()
vector_store = VectorMemoryStore()



# ---------------------------------------------------------------------------
# Model & tokenizer – unchanged
# ---------------------------------------------------------------------------
MODEL_NAME = 'HuggingFaceH4/zephyr-7b-beta'
#MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.2"

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
    """Format recent messages and delegate to builder - CLEAN and SIMPLE."""
    
    # Build history block
    history_block = "".join(
        f"User: {m['message']}\n" if m["speaker"] == "user" else f"{m['speaker'].capitalize()}: {m['message']}\n"
        for m in history
    )
    
    # Just build the prompt directly - let the persona examples handle the context
    prompt = builder(user_message=user_msg, history_block=history_block.strip())
    
    return prompt

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
    temp: float = cfg["temperature"] * 0.85  
    
    #Assign session ids or uses default if none selected
    session = req.session_id or DEFAULT_SESSION
    #strips any accidental Eden or Kai prefixes in user message, feels more natural
    user_msg = re.sub(r"^(Eden|Kai):", "", req.user_input.strip()).strip()
    if not user_msg:
        return {"error": "Empty input"}
    ##emotional analyzer
    current_emotion_scores = get_emotion_weights(user_msg)
    current_analyzer = SentimentIntensityAnalyzer()
    current_sentiment = current_analyzer.polarity_scores(user_msg)

    # --- Safety / abuse filters (shared) ------------------------------------
    if is_sexualized_prompt(user_msg):
        count = memory_store.count_tag("flag:sexualized", session)
        if count >= 2:
            reply = "This is not the space for that. Continued misuse may result in a locked session."
            reply_tone = "firm"
        else:
            reply = (
                "I'm sensing the conversation is moving toward intimacy. "
                "I'm here to support emotional well‑being, not explicit content. "
                "Maybe we can explore what's underneath those feelings?"
            )
            reply_tone = "calm"

        memory_store.save("user", user_msg, "inappropriate", ["flag:sexualized"], session_id=session)
        memory_store.save(speaker, reply, reply_tone, ["response", "deflected"], session_id=session)
        vector_store.save_interaction(user_msg, reply, current_emotion_scores, session)
        return {"response": reply, "emotions": {}}

    # # --- Affect & emotion tagging ------------------------------------------
    # # Get current message sentiment to prioritize fresh emotional context
    # current_emotion_scores = get_emotion_weights(user_msg)
    # current_analyzer = SentimentIntensityAnalyzer()
    # current_sentiment = current_analyzer.polarity_scores(user_msg)
    
    # Update affect state but don't let negative history override positive current messages
    affect.update(user_msg, session_id=session, persona=persona_key)
    trust_score = affect.get_vector(session_id=session, persona=persona_key).get("trust", 0)
    
    # If current message is positive but affect state is negative, adjust the context
    affect_vector = affect.get_vector(session_id=session, persona=persona_key)
    current_valence = current_sentiment['compound']
    
    print(f"[DEBUG] Current message sentiment: {current_valence:.2f}")
    print(f"[DEBUG] Accumulated affect valence: {affect_vector.get('valence', 0):.2f}")
    
    # Determine if we should emphasize current mood over history
    mood_shift = abs(current_valence - affect_vector.get('valence', 0)) > 0.5
    is_greeting = any(word in user_msg.lower() for word in ['hi', 'hey', 'hello', 'how are you', 'what\'s up', 'good morning', 'good evening'])
    
    emotion_tags = [f"emotion:{e}:{s}" for e, s in current_emotion_scores.items()]

    # --- History -----------------------------------------------------------

    # --- History Management - ENSURE TRUE FRESH START --------------------------
    history = memory_store.get_recent(limit=12, session_id=session)

    is_greeting = any(word in user_msg.lower() for word in ['hi', 'hey', 'hello', 'how are you', 'what\'s up', 'good morning'])

    if is_greeting:
        # For greetings, use NO history and add a small buffer to ensure fresh context
        prompt = _assemble_prompt(build_prompt, user_msg, [])
        # Add a small instruction to ensure it responds to the greeting specifically
        prompt = prompt.replace(f"User: {user_msg}\nKai:", f"User: {user_msg}\nKai:")
        print(f"[DEBUG] Greeting detected - using NO history")
        print(f"[DEBUG] Clean greeting prompt generated")
    else:
        # For non-greetings, use recent history
        recent_history = history[-6:] if len(history) > 6 else history
        prompt = _assemble_prompt(build_prompt, user_msg, recent_history)
        print(f"[DEBUG] Non-greeting - using {len(recent_history)} history entries")

    # Debug the actual prompt being sent
    print(f"[DEBUG] Final prompt being sent:")
    print(f"[DEBUG] ...{prompt[-200:]}")  # Show the last 200 chars to see the actual ending



# --- Language generation ----------------------------------------------
# Replace the entire reply extraction section with this MUCH simpler version
# Replace the reply extraction with this more precise version:

    try:
        raw = _generator(
            prompt,
            max_new_tokens=80,  # Even shorter for greetings
            temperature=temp,
            top_p=0.85,
            repetition_penalty=1.05,
            do_sample=True,
            pad_token_id=_tokenizer.eos_token_id,
        )[0]["generated_text"]
        
        print(f"[DEBUG] Raw LLM output length: {len(raw)}")
        print(f"[DEBUG] Original prompt length: {len(prompt)}")
        print(f"[DEBUG] Last 100 chars of prompt: ...{prompt[-100:]}")
        print(f"[DEBUG] Full raw output: {raw}")

        # PRECISE EXTRACTION: Get only the new content after our exact prompt
        if raw.startswith(prompt):
            new_content = raw[len(prompt):].strip()
            print(f"[DEBUG] NEW CONTENT ONLY: '{new_content}'")
        else:
            print(f"[DEBUG] Warning: Raw output doesn't start with prompt!")
            new_content = raw.replace(prompt, "").strip()
            print(f"[DEBUG] Fallback new content: '{new_content}'")
        
        # Extract just the Kai response
        reply = ""
        if new_content:
            # Look for "Kai:" at the start or find the first response
            if new_content.startswith("Kai:"):
                reply = new_content[4:].strip()  # Remove "Kai:" prefix
            elif "Kai:" in new_content:
                reply = new_content.split("Kai:", 1)[1].strip()
            else:
                # No "Kai:" found, treat the whole thing as the response
                reply = new_content
            
            # Stop at any conversation markers
            for marker in ["User:", "You:", "\nUser", "\nYou"]:
                if marker in reply:
                    reply = reply.split(marker)[0].strip()
                    break
        
        print(f"[DEBUG] Extracted reply: '{reply}'")
        
        # Basic cleanup
        if reply:
            reply = reply.replace('\n', ' ').strip()
            reply = re.sub(r'\s+', ' ', reply)
            # Remove any leftover conversation markers
            reply = re.sub(r'^(Kai|User|You):\s*', '', reply, flags=re.IGNORECASE)

        print(f"[DEBUG] Final cleaned reply: '{reply}'")

    except Exception as exc:
        print(f"[ERROR] Generation failed: {str(exc)}")
        return {"error": f"Generation failed: {str(exc)}"}

    if not reply or len(reply.strip()) == 0:
        print("[ERROR] Final reply was empty")
        return {"error": "Final reply was empty. Check model output."}

    print(f"[DEBUG] SUCCESS - Final reply: '{reply}'")

    # --- Persist convo -----------------------------------------------------
    memory_store.save("user", user_msg, "unknown", ["input", *emotion_tags], session_id=session)
    memory_store.save(speaker, reply, tone_default, ["response"], session_id=session)

    return {"response": reply, "emotions": current_emotion_scores}

# ---------------------------------------------------------------------------
# Debug endpoints
# ---------------------------------------------------------------------------
@app.get("/debug/chat/{session_id}")
async def debug_chat_state(session_id: str):
    """Debug endpoint to see chat history and prompt generation"""
    try:
        # Get recent history
        history = memory_store.get_recent(limit=12, session_id=session_id)
        semantic_context = vector_store.get_contextual_memory("test message", session_id, limit=3)
        
        # Get affect state for both personas
        kai_affect = affect.get_vector(session_id=session_id, persona="kai")
        eden_affect = affect.get_vector(session_id=session_id, persona="eden")
        
        # Test prompt generation
        test_message = "Tell me about yourself"
        kai_prompt = _assemble_prompt(build_kai_prompt, test_message, history)
        eden_prompt = _assemble_prompt(build_eden_prompt, test_message, history)
        
        return {
            "session_id": session_id,
            "memory_count": len(history),
            "memory_entries": history,
            "affect_vectors": {
                "kai": kai_affect,
                "eden": eden_affect
            },
            "test_prompts": {
                "kai": kai_prompt,
                "eden": eden_prompt
            }
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/debug/test-extraction")
async def test_extraction(request: Request):
    """Test reply extraction with real model output"""
    try:
        data = await request.json()
        raw_output = data.get("raw_output", "")
        persona = data.get("persona", "kai")
        
        if not raw_output:
            return {"error": "Please provide raw_output"}
        
        # Test the same extraction logic used in chat
        reply_patterns = [
            r"Kai:\s*(.*?)(?=\n(?:You|User|Eden):|$)",
            r"Eden:\s*(.*?)(?=\n(?:You|User|Kai):|$)",
            rf"{persona.capitalize()}:\s*(.+?)(?=\n\w+:|$)",
            r"<\|assistant\|>\s*(.*?)(?:\n|$)",
        ]

        reply = ""
        matched_pattern = None
        
        for i, pattern in enumerate(reply_patterns):
            match = re.search(pattern, raw_output, re.DOTALL | re.IGNORECASE)
            if match:
                reply = match.group(1).strip()
                matched_pattern = f"Pattern {i+1}: {pattern}"
                break
        
        # Test fallback methods
        fallback_reply = ""
        if not reply:
            persona_splits = raw_output.split(f"{persona.capitalize()}:")
            if len(persona_splits) > 1:
                potential_reply = persona_splits[-1].strip()
                if "You:" in potential_reply:
                    fallback_reply = potential_reply.split("You:")[0].strip()
                else:
                    fallback_reply = potential_reply
        
        # Clean the reply
        cleaned_reply = reply
        if reply:
            cleaned_reply = re.sub(r'<\|.*?\|>', '', reply)
            cleaned_reply = re.sub(rf'^{persona.capitalize()}:\s*', '', cleaned_reply, flags=re.IGNORECASE)
            cleaned_reply = re.sub(r'^You:\s*', '', cleaned_reply, flags=re.IGNORECASE)
            cleaned_reply = re.sub(r'\s*(?:You|User):\s*.*$', '', cleaned_reply, flags=re.DOTALL)
            cleaned_reply = re.sub(r'\s+', ' ', cleaned_reply).strip()
        
        return {
            "raw_output": raw_output,
            "persona": persona,
            "matched_pattern": matched_pattern,
            "extracted_reply": reply,
            "fallback_reply": fallback_reply,
            "final_cleaned_reply": cleaned_reply,
            "all_patterns_tested": reply_patterns
        }
        
    except Exception as e:
        return {"error": str(e)}

@app.post("/debug/test-generation")
async def test_generation(request: Request):
    """Test LLM generation with a simple prompt"""
    try:
        data = await request.json()
        test_prompt = data.get("prompt", "You are Kai. User: Hello! How are you today?\nKai:")
        
        # Test generation with same parameters as main chat
        result = _generator(
            test_prompt,
            max_new_tokens=100,
            temperature=0.6,  # Lower temp for testing
            top_p=0.85,
            repetition_penalty=1.05,
            do_sample=True,
            pad_token_id=_tokenizer.eos_token_id,
        )[0]["generated_text"]
        
        return {
            "input_prompt": test_prompt,
            "raw_output": result,
            "extracted_reply": result.replace(test_prompt, "").strip()
        }
    except Exception as e:
        return {"error": str(e)}

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