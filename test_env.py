import os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY is not found in the environment.")
else:
    print(f"GEMINI_API_KEY: {GEMINI_API_KEY}")