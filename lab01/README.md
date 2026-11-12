# Lab 1 — Local Inference & the OpenAI Protocol

`chat_ollama.py`: interactive CLI chat with a local Ollama model (`qwen2.5:1.5b`) through the OpenAI-compatible endpoint `http://localhost:11434/v1/chat/completions`. The whole conversation history (system prompt + every user/assistant message) is sent on each turn, so the model keeps the context across turns.

```powershell
ollama pull qwen2.5:1.5b
python lab01/chat_ollama.py      # type 'exit' to quit
```
