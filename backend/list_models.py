from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

keys = os.getenv("GEMINI_API_KEYS", "").split(",")
if not keys or not keys[0]:
    print("No API key found.")
    exit(1)

client = genai.Client(api_key=keys[0])

print("Available Models supporting generateContent:")
print("-" * 50)

try:
    for model in client.models.list():
        print(f"- {model.name}")
except Exception as e:
    print(f"Error listing models: {e}")
