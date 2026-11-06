import httpx
from typing import Optional, Dict, Any

class ScraperService:
    """Tầng dịch vụ cào dữ liệu từ các sàn thương mại điện tử."""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    async def fetch_html(self, url: str) -> Optional[str]:
        async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=10.0) as client:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return resp.text
            except Exception:
                return None
        return None
