import os
from google import genai
from .settings import settings

def get_gemini_client() -> genai.Client:
    """Khởi tạo và trả về Google GenAI Client với API Key đã cấu hình."""
    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
    return genai.Client(api_key=api_key)

def get_model_name() -> str:
    """Trả về tên model Gemini mặc định."""
    return settings.GEMINI_MODEL
