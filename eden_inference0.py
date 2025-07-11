from transformers import pipeline

#Load the pipeline (e.g. for sentiment-analysis)
generator = pipeline("text-generation", model="gpt2")

#Sample input
prompt = "In a world where AI feel emotions"

#Generate output
output = generator(
    prompt, 
    max_new_tokens=50, 
    num_return_sequences=1,
    truncation=True,
    pad_token_id=50256
    )

print("Generated text:")
print(output[0]["generated_text"])

