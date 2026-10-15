import os
from dotenv import load_dotenv
from google import genai

# Load environment variables from .env into os.environ
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
assert api_key and api_key != "PUNE_AICI_CHEIA_TA", "ERROR: GEMINI_API_KEY not found. Check your .env file!"

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

# Initialize the client (automatically reads GEMINI_API_KEY from os.environ)
client = genai.Client()

response = client.models.generate_content(
    model=MODEL,
    contents="Reply with the exact phrase: 'Telemetry online.'"
)
print(response.text)
