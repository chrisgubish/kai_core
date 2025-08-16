import torch
import os
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from dotenv import load_dotenv

# Load your environment variables (HF_TOKEN still useful for other models)
load_dotenv()

print("Starting Zephyr 7B test...")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"GPU memory before loading: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")

# Configure 4-bit quantization
quant_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True
)

# Zephyr model - NO APPROVAL NEEDED!
MODEL_NAME = "HuggingFaceH4/zephyr-7b-beta"

print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

print("Loading model (this will take 2-5 minutes for first download)...")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=quant_config,
    device_map="auto",
    torch_dtype=torch.float16,
    trust_remote_code=True
)

print("Model loaded successfully!")
print(f"GPU memory after loading: {torch.cuda.memory_allocated() / 1024**3:.1f}GB")

# Test generation with Zephyr's chat format
system_msg = "You are Kai, a warm and supportive friend who listens without judgment."
user_msg = "Hey Kai! I'm having a rough day, how are you?"

# Zephyr uses a specific chat template
chat = [
    {"role": "system", "content": system_msg},
    {"role": "user", "content": user_msg}
]

# Apply chat template
prompt = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)

print("Testing generation...")
inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
with torch.no_grad():
    outputs = model.generate(
        **inputs,
        max_new_tokens=80,
        temperature=0.7,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id
    )

# Extract just the new response
full_response = tokenizer.decode(outputs[0], skip_special_tokens=True)
response = full_response.replace(prompt, "").strip()

print("\nTest Response:")
print(f"Kai: {response}")
print("\n Zephyr 7B is working!")