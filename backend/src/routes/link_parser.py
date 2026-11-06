from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.tools.url_extractor import UrlExtractorTool

router = APIRouter(prefix="/parse-link", tags=["Link Parser"])
extractor = UrlExtractorTool()

class ParseLinkRequest(BaseModel):
    url: str

@router.post("")
@router.post("/parse")
async def parse_product_link(req: ParseLinkRequest):
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp đường dẫn URL hợp lệ.")
    try:
        data = await extractor.run(url=req.url.strip())
        return {"status": "success", "product": data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Không thể bóc tách liên kết: {str(e)}")
