# execution/auth.py
import json, logging, pyotp
from pathlib import Path
from datetime import date
from kiteconnect import KiteConnect
import config

log = logging.getLogger(__name__)
TOKEN_FILE = Path("token_cache.json")

def _get_kite():
    return KiteConnect(api_key=config.API_KEY)

def _save_token(token: str):
    TOKEN_FILE.write_text(json.dumps({
        "token": token,
        "date": str(date.today())
    }))

def _load_cached_token():
    if not TOKEN_FILE.exists():
        return None
    data = json.loads(TOKEN_FILE.read_text())
    if data.get("date") == str(date.today()):
        return data.get("token")
    return None

def _fresh_login(kite: KiteConnect) -> str:
    print(f"\nOpen this URL in your browser:\n{kite.login_url()}\n")
    request_token = input("Paste the request_token from redirect URL: ").strip()
    session = kite.generate_session(
        request_token,
        api_secret=config.API_SECRET
    )
    return session["access_token"]

def load_session() -> KiteConnect:
    kite = _get_kite()
    token = _load_cached_token()
    if token:
        try:
            kite.set_access_token(token)
            kite.profile()
            log.info("Session loaded from cache")
            return kite
        except Exception:
            log.warning("Cached token invalid, re-logging in")
    token = _fresh_login(kite)
    _save_token(token)
    kite.set_access_token(token)
    log.info("Fresh session created")
    return kite