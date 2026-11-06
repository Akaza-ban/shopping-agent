"""Chỉ dẫn ngôn ngữ trả lời, nối vào cuối system prompt (mặc định tiếng Việt: không thêm gì)."""

_ENGLISH = (
    "\n\nLANGUAGE: Write the entire answer in English. Keep product names, prices (VND), "
    "platform names and technical specs exactly as provided; do not translate product names."
)


def language_instruction(language: str) -> str:
    return _ENGLISH if language == "en" else ""
