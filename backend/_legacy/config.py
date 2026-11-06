"""Root config.py re-exporting from src.config for convenient access."""
from src.config import settings, get_chat_model, Settings

__all__ = ["settings", "get_chat_model", "Settings"]
