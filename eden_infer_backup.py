# eden_infer.py

import os
from eden_memory import EdenMemory
from llama_cpp import Llama

MODEL_PATH = os.getenv("EDEN_MODEL_PATH", "C:\\Models\\mistral-7b-instruct.Q4_K_M.gguf")

class EdenLLM:
    def __init__(self, model_path: str = MODEL_PATH):
        self.model_path = model_path
        try:
            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=8192,
                n_threads=6
            )
        except Exception as e:
            print(f"[WARN] LLM not loaded yet: {e}")
            self.llm = None

        self.memory = EdenMemory()

    def chat(self, user_id: str, user_msg: str) -> str:
        context = self.memory.compile_prompt_context(user_id)
        prompt = (
            "You are Eden, an emotionally intelligent AI.\n"
            f"{context}"
            f"[User]: {user_msg}\n[Eden]:"
        )

        if not self.llm:
            return "[Eden]: Model not available yet. Please finish downloading the GGUF file."

        try:
            output = self.llm(prompt, max_tokens=512, stop=["[User]:"])
            return output["choices"][0]["text"].strip()
        except Exception as e:
            return f"[Eden]: Failed to generate response: {e}"


# --- Optional: test wrapper init without inference ---
if __name__ == "__main__":
    eden = EdenLLM()
    print("EdenLLM initialized. Waiting for model file to complete.")
