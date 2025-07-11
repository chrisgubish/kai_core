from eden_infer import EdenLLM

eden = EdenLLM()

user_id = "test_user"

messages = [
    "Hello Eden, what are you?",
    "Can you remember what I just said?",
    "How do you feel about humans?",
    "What’s your main purpose?"
]

print("Starting Eden multi-turn test...\n")

for i, msg in enumerate(messages, 1):
    print(f"  User ({i}): {msg}")
    response = eden.chat(user_id=user_id, user_msg=msg)
    print(f" Eden: {response}\n")