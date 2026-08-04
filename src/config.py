import os
from typing import List, Optional

def _default_dir(path: str, fallback_relative: str) -> str:
    """Helper to use system path if writable, or fallback to relative project dir."""
    try:
        os.makedirs(path, exist_ok=True)
        return path
    except (PermissionError, OSError):
        rel = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", fallback_relative))
        os.makedirs(rel, exist_ok=True)
        return rel

class Settings:
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_ALLOWED_USERS: List[int] = [
        int(uid.strip()) for uid in os.getenv("TELEGRAM_ALLOWED_USERS", "").split(",") if uid.strip().isdigit()
    ]

    # AI / LLM Engine (Gemini API & DigitalOcean Inference)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL_NAME: str = os.getenv("GEMINI_MODEL_NAME", "gemini-3.1-flash-lite")
    MAX_CHAT_HISTORY_TURNS: int = int(os.getenv("MAX_CHAT_HISTORY_TURNS", "4")) # Only send last 4 turns to AI

    # Storage Paths & SQLite Database
    SCRATCH_DIR: str = os.getenv("SCRATCH_DIR", _default_dir("/var/blaine/scratch", "data/scratch"))
    ORGANIZED_DIR: str = os.getenv("ORGANIZED_DIR", _default_dir("/var/blaine/organized", "data/organized"))
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", os.path.join(_default_dir("/var/blaine", "data"), "blaine.db"))

    # YT-DLP / YouTube Authentication Configuration
    YTDLP_COOKIES_PATH: str = os.getenv("YTDLP_COOKIES_PATH", "/var/blaine/cookies.txt")
    YTDLP_COOKIES_FROM_BROWSER: Optional[str] = os.getenv("YTDLP_COOKIES_FROM_BROWSER", None)

    # Cloud Remotes (Rclone names for MEGA S3 & Google Drive)
    MEGA_S3_REMOTE: str = os.getenv("MEGA_S3_REMOTE", "mega-s3:blaine-archives")
    GDRIVE_REMOTE: str = os.getenv("GDRIVE_REMOTE", "gdrive:BlaineMedia")

    # Redis Queue
    REDIS_HOST: str = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))

    # Web Search API (Brave Search)
    BRAVE_API_KEY: str = os.getenv("BRAVE_API_KEY", "")

settings = Settings()
