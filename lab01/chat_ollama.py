import requests

url = "http://localhost:11434/v1/chat/completions"

# 1. Definim istoricul conversației și adăugăm promptul de sistem (rolul)
history = [
    {
        "role": "system",
        "content": "Ești un asistent util care răspunde scurt și la obiect."
    }
]

print("=== Conversație Ollama (Scrie 'exit' pentru a închide) ===")

while True:
    user_input = input("\nTu: ")
    if user_input.lower() in ["exit", "quit"]:
        break

    # 2. Adăugăm mesajul utilizatorului în istoric
    history.append({"role": "user", "content": user_input})

    payload = {
        "model": "qwen2.5:1.5b",
        "messages": history,  # Trimitere întregului istoric la Ollama
        "temperature": 0.7
    }

    try:
        response = requests.post(url, json=payload)
        bot_response = response.json()["choices"][0]["message"]["content"]
        
        # 3. Adăugăm răspunsul modelului în istoric pentru cererile viitoare
        history.append({"role": "assistant", "content": bot_response})
        
        print(f"\nOllama: {bot_response}")
    except Exception as e:
        print(f"\nEroare la conectare: {e}")