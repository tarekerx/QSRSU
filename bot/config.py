import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
IMAGE_DIR: str = os.getenv("IMAGE_DIR", "images")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in .env")

# Fail fast at startup: without an API key photo transcription cannot work,
# so print a readable error and stop instead of failing later on every photo.
if not GROQ_API_KEY:
    print("ERROR: GROQ_API_KEY is not set in .env - add it before starting the bot.")
    raise SystemExit(1)

# Same idea for the answering step: no key means no solving, so stop early.
if not GEMINI_API_KEY:
    print("ERROR: GEMINI_API_KEY is not set in .env - add it before starting the bot.")
    raise SystemExit(1)