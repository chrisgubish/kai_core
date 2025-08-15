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
# Imports — (unchanged from your previous file, but grouped logically)
# ---------------------------------------------------------------------------
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
from jose import JWTError, jwt
from passlib.context import CryptContext
import json
import uuid
from pydantic import BaseModel
from pathlib import Path

# Fixed imports - adjust these based on your actual file structure
try:
    from backend.memory.embeddings import EmbeddingPipeline
except ImportError:
    # Fallback for different project structures
    try:
        from embeddings import EmbeddingPipeline
    except ImportError:
        # Create a simple fallback
        class EmbeddingPipeline:
            def __init__(self):
                pass
            def encode_conversation(self, user_msg: str, ai_response: str):
                return [0.0] * 384  # Default embedding size

import chromadb

from collections import defaultdict

from threading import Thread
from typing import List, Dict, Callable, Optional
import os, re, torch
from datetime import datetime, timedelta

from dotenv import load_dotenv

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    pipeline,
    BitsAndBytesConfig,
)

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Fixed imports - adjust these based on your actual file structure
try:
    from backend.inference.affect import Affect_State
    from backend.memory.memory_store import Memory_Store
    from backend.memory.vector_memory_store import VectorMemoryStore
    from backend.memory.eden_memory_defender import (
        is_sexualized_prompt,
        is_racist_prompt,
        is_troll_prompt,
        is_shock_prompt,
    )
    from backend.persona.kai_persona import build_prompt as build_kai_prompt
    from backend.persona.eden_persona import build_prompt as build_eden_prompt
    from backend.persona.scheduler import run_scheduler, stop_scheduler
except ImportError:
    # Fallback imports for when files are in the same directory or different structure
    try:
        from affect import Affect_State
        from memory_store import Memory_Store
        from vector_memory_store import VectorMemoryStore
        from eden_memory_defender import (
            is_sexualized_prompt,
            is_racist_prompt,
            is_troll_prompt,
            is_shock_prompt,
        )
        from kai_persona import build_prompt as build_kai_prompt
        from eden_persona import build_prompt as build_eden_prompt
        from scheduler import run_scheduler, stop_scheduler
    except ImportError:
        print("[WARNING] Some modules not found. Creating fallback implementations...")
        
        # Fallback implementations
        class Affect_State:
            def __init__(self):
                self.states = defaultdict(lambda: {"valence": 0, "arousal": 0, "dominance": 0, "trust": 0})
            def update(self, text: str, session_id: str, persona: str = "eden"):
                pass
            def get_vector(self, session_id: str, persona: str = "eden"):
                return self.states[(session_id, persona)]

        class Memory_Store:
            def __init__(self):
                self.sessions = defaultdict(list)
            def save(self, speaker: str, message: str, emotion: str = "neutral", tags: list = None, session_id: str = "default"):
                entry = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "speaker": speaker,
                    "message": message,
                    "emotion": emotion,
                    "tags": tags or []
                }
                self.sessions[session_id].append(entry)
            def get_recent(self, limit: int = 10, session_id: str = "default", **kwargs):
                return self.sessions[session_id][-limit:]
            def count_tag(self, tag: str, session_id: str = "default"):
                count = 0
                for entry in self.sessions[session_id]:
                    if tag in entry.get("tags", []):
                        count += 1
                return count
            def clear(self, session_id: str = "default"):
                self.sessions[session_id] = []
            def clear_all(self):
                self.sessions.clear()

        class VectorMemoryStore:
            def __init__(self):
                pass
            def save_interaction(self, user_msg: str, ai_response: str, emotional_data: dict, session_id: str):
                pass
            def get_contextual_memory(self, query: str, session_id: str, limit: int = 3):
                return []

        def is_sexualized_prompt(text: str) -> bool:
            return False
        def is_racist_prompt(text: str) -> bool:
            return False
        def is_troll_prompt(text: str) -> bool:
            return False
        def is_shock_prompt(text: str) -> bool:
            return False

        def build_kai_prompt(user_message: str, history_block: str = "") -> str:
            return f"You are Kai, a friendly and supportive companion.\n\n{history_block}\nUser: {user_message}\nKai:"

        def build_eden_prompt(user_message: str, history_block: str = "") -> str:
            return f"You are Eden, a caring and empathetic guide.\n\n{history_block}\nUser: {user_message}\nEden:"

        def run_scheduler():
            pass
        def stop_scheduler():
            pass

# Local imports
try:
    from emotion_weights import get_emotion_weights
    from tone_adapter import friendify, force_casual, is_formal_essay
except ImportError:
    # If these don't exist, create simple fallback functions
    def get_emotion_weights(text: str) -> dict:
        return {}
    
    def friendify(text: str) -> str:
        return text
    
    def force_casual(text: str) -> str:
        return text
    
    def is_formal_essay(text: str) -> bool:
        return False

# ---------------------------------------------------------------------------
# Environment + FastAPI init
# ---------------------------------------------------------------------------
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated='auto')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Fixed user database
users_db = {}

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

HF_TOKEN = os.getenv("HF_TOKEN")

# Creates FastAPI app object instance
app = FastAPI()

# Enables Cross-Origin Resource Sharing so frontend can talk with backend
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

# Base directory in relation to current API path location
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------

# Pulls Affect_State and Memory_Store classes and creates class instances in API
affect = Affect_State()
memory_store = Memory_Store()
vector_store = VectorMemoryStore()

# ---------------------------------------------------------------------------
# Model & tokenizer — unchanged
# ---------------------------------------------------------------------------
MODEL_NAME = 'HuggingFaceH4/zephyr-7b-beta'

# Allows for 4-bit quantization through BitsAndBytesConfig
quant_cfg = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16)

print(f"[STARTUP] Loading model {MODEL_NAME}...")
try:
    _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, token=HF_TOKEN)
    _model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        device_map="auto",
        quantization_config=quant_cfg,
        token=HF_TOKEN,
    )

    _generator = pipeline(
        "text-generation",
        model=_model,
        tokenizer=_tokenizer,
        torch_dtype=torch.float16,
    )
    print(f"[STARTUP] Model loaded successfully!")
except Exception as e:
    print(f"[ERROR] Failed to load model: {e}")
    print("[FALLBACK] Creating dummy generator for testing...")
    
    class DummyGenerator:
        def __call__(self, prompt, **kwargs):
            # Simple fallback response for testing
            if "kai" in prompt.lower():
                return [{"generated_text": prompt + " Hey! What's up?"}]
            else:
                return [{"generated_text": prompt + " Hello, I'm here to listen."}]
    
    _generator = DummyGenerator()
    _tokenizer = None

# ---------------------------------------------------------------------------
# WebSocket Connection Manager
# ---------------------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, str] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_sessions[user_id] = f"session_{user_id}_{int(datetime.now().timestamp())}"

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]

    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)

manager = ConnectionManager()

# ---------------------------------------------------------------------------
# Persona registry — add new voices here
# ---------------------------------------------------------------------------
PersonaConfig = Dict[str, str | Callable]

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
class ChatRequest(BaseModel):
    user_input: str
    session_id: str | None = DEFAULT_SESSION
    persona: str | None = "eden"

# ---------------------------------------------------------------------------
# Helper — build prompt with persona history injection
# ---------------------------------------------------------------------------

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
# WebSocket endpoint for real-time chat
# ---------------------------------------------------------------------------

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    # Simple auth bypass for development - implement proper auth later
    await manager.connect(websocket, user_id)
    session_id = manager.user_sessions[user_id]

    try:
        while True:
            # Receive message from WebSocket
            data = await websocket.receive_json()
            user_input = data.get("message", "").strip()
            persona = data.get("persona", "eden").lower()

            if not user_input:
                continue

            # Send typing indicator
            typing_response = {
                "type": "typing",
                "content": f"{persona.capitalize()} is typing...",
                "persona": persona
            }
            await websocket.send_text(json.dumps(typing_response))

            # Load persona config
            persona_key = persona.lower()
            cfg = PERSONAS.get(persona_key)
            if cfg is None:
                error_response = {
                    "type": "error",
                    "content": "Unknown persona",
                    "persona": persona
                }
                await websocket.send_text(json.dumps(error_response))
                continue

            build_prompt: Callable[[str, str], str] = cfg["builder"]
            speaker: str = cfg["speaker"]
            tone_default: str = cfg["default_tone"]
            temp: float = cfg["temperature"] * 0.85
            
            # Strip any accidental Eden or Kai prefixes
            user_msg = re.sub(r"^(Eden|Kai):", "", user_input).strip()
            if not user_msg:
                error_response = {
                    "type": "error",
                    "content": "Empty input",
                    "persona": persona
                }
                await websocket.send_text(json.dumps(error_response))
                continue

            # Emotional analyzer
            current_emotion_scores = get_emotion_weights(user_msg)
            current_analyzer = SentimentIntensityAnalyzer()
            current_sentiment = current_analyzer.polarity_scores(user_msg)

            # Safety / abuse filters
            if is_sexualized_prompt(user_input):
                count = memory_store.count_tag("flag:sexualized", session_id)
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

                memory_store.save("user", user_msg, "inappropriate", ["flag:sexualized"], session_id=session_id)
                memory_store.save(speaker, reply, reply_tone, ["response", "deflected"], session_id=session_id)
                
                response_data = {
                    "type": "message",
                    "content": reply,
                    "emotions": {},
                    "persona": persona_key
                }
                await websocket.send_text(json.dumps(response_data))
                continue

            # Update affect state
            affect.update(user_msg, session_id=session_id, persona=persona_key)
            trust_score = affect.get_vector(session_id=session_id, persona=persona_key).get("trust", 0)
            
            # Get current message sentiment to prioritize fresh emotional context
            affect_vector = affect.get_vector(session_id=session_id, persona=persona_key)
            current_valence = current_sentiment['compound']
            
            print(f"[DEBUG] Current message sentiment: {current_valence:.2f}")
            print(f"[DEBUG] Accumulated affect valence: {affect_vector.get('valence', 0):.2f}")
            
            emotion_tags = [f"emotion:{e}:{s}" for e, s in current_emotion_scores.items()]

            # History Management
            history = memory_store.get_recent(limit=12, session_id=session_id)
            is_greeting = any(word in user_msg.lower() for word in ['hi', 'hey', 'hello', 'how are you', 'what\'s up', 'good morning'])

            if is_greeting:
                # For greetings, use NO history
                prompt = _assemble_prompt(build_prompt, user_msg, [])
                print(f"[DEBUG] Greeting detected - using NO history")
            else:
                # For non-greetings, use recent history
                recent_history = history[-6:] if len(history) > 6 else history
                prompt = _assemble_prompt(build_prompt, user_msg, recent_history)
                print(f"[DEBUG] Non-greeting - using {len(recent_history)} history entries")

            # Language generation
            try:
                raw = _generator(
                    prompt,
                    max_new_tokens=80,
                    temperature=temp,
                    top_p=0.85,
                    repetition_penalty=1.05,
                    do_sample=True,
                    pad_token_id=_tokenizer.eos_token_id if _tokenizer else None,
                )[0]["generated_text"]
                
                print(f"[DEBUG] Raw LLM output length: {len(raw)}")
                print(f"[DEBUG] Original prompt length: {len(prompt)}")

                # Extract only the new content after our exact prompt
                if raw.startswith(prompt):
                    new_content = raw[len(prompt):].strip()
                    print(f"[DEBUG] NEW CONTENT ONLY: '{new_content}'")
                else:
                    print(f"[DEBUG] Warning: Raw output doesn't start with prompt!")
                    new_content = raw.replace(prompt, "").strip()
                    print(f"[DEBUG] Fallback new content: '{new_content}'")
                
                # Extract just the persona response
                reply = ""
                if new_content:
                    # Look for "Kai:" or "Eden:" at the start
                    persona_prefix = f"{speaker.capitalize()}:"
                    if new_content.startswith(persona_prefix):
                        reply = new_content[len(persona_prefix):].strip()
                    elif persona_prefix in new_content:
                        reply = new_content.split(persona_prefix, 1)[1].strip()
                    else:
                        # No persona prefix found, treat the whole thing as the response
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
                    reply = re.sub(r'^(Kai|Eden|User|You):\s*', '', reply, flags=re.IGNORECASE)

                print(f"[DEBUG] Final cleaned reply: '{reply}'")

            except Exception as exc:
                print(f"[ERROR] Generation failed: {str(exc)}")
                error_response = {
                    "type": "error",
                    "content": f"Generation failed: {str(exc)}",
                    "persona": persona
                }
                await websocket.send_text(json.dumps(error_response))
                continue

            if not reply or len(reply.strip()) == 0:
                print("[ERROR] Final reply was empty")
                error_response = {
                    "type": "error", 
                    "content": "Final reply was empty. Check model output.",
                    "persona": persona
                }
                await websocket.send_text(json.dumps(error_response))
                continue

            print(f"[DEBUG] SUCCESS - Final reply: '{reply}'")

            # Persist conversation
            memory_store.save("user", user_msg, "unknown", ["input", *emotion_tags], session_id=session_id)
            memory_store.save(speaker, reply, tone_default, ["response"], session_id=session_id)

            # Send response back to client
            response_data = {
                "type": "message",
                "content": reply,
                "emotions": current_emotion_scores,
                "persona": persona_key
            }
            await websocket.send_text(json.dumps(response_data))

    except WebSocketDisconnect:
        manager.disconnect(user_id)
        print(f"User {user_id} disconnected")
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
        manager.disconnect(user_id)

# ---------------------------------------------------------------------------
# Authentication endpoints
# ---------------------------------------------------------------------------
@app.post("/register")
async def register(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username in users_db:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = get_password_hash(form_data.password)
    user_id = str(uuid.uuid4())
    users_db[form_data.username] = {
        "id": user_id,
        "username": form_data.username,
        "hashed_password": hashed_password
    }
    return {"message": "User registered successfully", "user_id": user_id}

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users_db.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user["id"]
    }

# ---------------------------------------------------------------------------
# Debug endpoints
# ---------------------------------------------------------------------------
@app.get("/debug/chat/{session_id}")
async def debug_chat_state(session_id: str):
    """Debug endpoint to see chat history and prompt generation"""
    try:
        # Get recent history
        history = memory_store.get_recent(limit=12, session_id=session_id)
        
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

# ---------------------------------------------------------------------------
# Health check endpoint
# ---------------------------------------------------------------------------
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "personas": list(PERSONAS.keys()),
        "model": MODEL_NAME,
        "active_connections": len(manager.active_connections),
        "model_loaded": _tokenizer is not None
    }

# ---------------------------------------------------------------------------
# Misc endpoints
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {"message": "Kai Chat API", "health": "/health", "docs": "/docs"}

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
# Scheduler hooks
# ---------------------------------------------------------------------------
scheduler_thread = None

@app.on_event("startup")
async def startup_event():
    global scheduler_thread
    try:
        scheduler_thread = Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        print("[FastAPI] Scheduler launched.")
    except Exception as e:
        print(f"[FastAPI] Scheduler failed to start: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    try:
        stop_scheduler()
        print("[FastAPI] Scheduler stopped.")
    except Exception as e:
        print(f"[FastAPI] Scheduler shutdown error: {e}")

# ---------------------------------------------------------------------------
# Dream log endpoint
# ---------------------------------------------------------------------------
@app.get("/dreamlog")
async def get_dreamlog(n: int = 5):
    try:
        from backend.persona.eden_monologue import get_recent_monologues
        logs = get_recent_monologues(n)
        return {"logs": logs}
    except Exception as e:
        return {"error": str(e), "logs": []}