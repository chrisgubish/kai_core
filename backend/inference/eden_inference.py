from transformers import pipeline
from affect import AffectState
from dotenv import load_dotenv
from memory.memory_store import Memory_Store
from affect import Affect_State
import torch
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# === Load environment variables ===
load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN", "your-default-token-or-warning")
CACHE_PATH = os.getenv("CACHE_PATH", "Z:/kai_core/models")
MODEL_PATH = os.getenv("EDEN_MODEL_PATH", "tiiuae/falcon-7b-instruct")

# === Initialize emotional affect tracker ===
affect = Affect_State()

# === Initialize Memory store ===
memory_store = Memory_Store()

# === Initialize text generation model ===
generator = pipeline(
    "text-generation",
    model=MODEL_PATH,
    torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
    device_map="auto",
    cache_dir=CACHE_PATH
)

# === Memory state ===
chat_history = ""

# === Main interaction loop ===
while True:
    user_input = input("You: ")
    if user_input.lower() in ("quit", "exit"):
        break

    session_id = "default"
    persona = "eden"


    # Update affect state
    affect.update(user_input, session_id, persona)
    print("Affect State:", affect.get_vector(session_id=session_id, persona=persona))

    # Update trust score
    trust_score = affect.get_vector(session_id=session_id, persona=persona).get("trust" , 0.0)

    # Format prompt
    prompt = (
        f"{chat_history}"
        f"[INST] (trust={trust_score:.2f}) {user_input} [/INST]\n"
    )

    # Generate response
    try:
        response = generator(prompt, max_new_tokens=100)[0]["generated_text"]
        cleaned = response.replace(prompt, "").strip()
    except Exception as e:
        print("Generation failed:", str(e))
        continue

    # Output and update memory
    print("\nEden:", cleaned)
    chat_history += f"You: {user_input}\nEden: {cleaned}\n"
