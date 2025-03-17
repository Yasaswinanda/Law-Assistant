import ollama

def check_ollama_connection():
    # Create a client instance; adjust host if needed
    client = ollama.Client()  # Defaults to http://localhost:11434
    
    # Define your prompts
    system_prompt = "You are a helpful AI assistant specialized in bioengineering."
    base_prompt = "Explain how CRISPR works in simple terms."
    
    # Call generate() on the client, passing both the system and base prompt.
    # (The ollama module passes additional keyword parameters directly to the API.)
    response = client.generate(
        model="gemma3:4b",
        system=system_prompt,
        prompt=base_prompt
    )
    
    # Print the returned response
    print("Model response:", response.get("response", "No response received."))

if __name__ == "__main__":
    check_ollama_connection()
