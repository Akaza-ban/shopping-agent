"""Biểu thức nhận diện câu hỏi dùng chung cho router và câu trả lời dựng sẵn (chỉ dùng khi LLM không trả lời được)."""

import re

OUT_OF_SCOPE_RE = re.compile(
    r"\b(?:vi[ếe]t\s+code|gi[ảa]i\s+to[áa]n|gi[ảa]i\s+ph??[ươo]ng\s+tr[ìi]nh|th[ờo]i\s+ti[ếe]t|l[àa]m\s+th[ơo]|"
    r"vi[ếe]t\s+th[ơo]|k[ểe]\s+chuy[ệe]n|c[ôo]ng\s+th[ứu]c\s+n[ấa]u|n[ấa]u\s+m[óo]n|b[ệe]nh\s+vi[ệe]n|"
    r"kh[áa]m\s+b[ệe]nh|ch[íi]nh\s+tr[ịi])\b"
)
# Xin tư vấn, phân vân lựa chọn ("nên mua A hay B")
ADVICE_RE = re.compile(
    r"\b(?:n[êe]n\s+mua|c[óo]\s+n[êe]n\s+mua|n[êe]n\s+ch[ọo]n|ph[âa]n\s+v[âa]n|t[ưu]\s+v[ấa]n\s+gi[úu]p)\b"
)
SEARCH_ACTION_RE = re.compile(
    r"\b(?:t[ìi]m\s+(?:cho\s+t[ôo]i|gi[úu]p|mua|n[ơo]i\s+b[áa]n)|qu[éae]t\s+gi[áa]|b[áa]o\s+gi[áa]|link\s+mua)\b"
)
GREETING_RE = re.compile(r"^(?:ch[àa]o|hi|hello|alo|h[ée]lo|[êe]|b[ạa]n\s+l[àa]\s+ai|t[ưu]\s+v[ấa]n\s+gi[úu]p)")
URL_RE = re.compile(r"https?://[^\s]+")
