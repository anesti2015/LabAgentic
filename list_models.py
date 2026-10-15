"""Utilitar: listeaza modelele Gemini disponibile pentru cheia ta (util daca un nume de model da 404)."""
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client()
for m in client.models.list():
    if "gemini" in m.name:
        print(m.name)
