# config.py
import os
from dotenv import load_dotenv

load_dotenv()

def get(key):
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(f"Missing required env var: {key}")
    return val

API_KEY     = get("API_KEY")
API_SECRET  = get("API_SECRET")
TOTP_SECRET = get("TOTP_SECRET")
TG_TOKEN    = get("TG_BOT_TOKEN")
TG_CHAT_ID  = get("TG_CHAT_ID")