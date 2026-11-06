from fastapi import APIRouter
from pydantic import BaseModel
from ...core.tools.url_extractor import UrlExtractorTool

router = APIRouter(prefix="/parse-link", tags=["Link Parser"])
extractor = UrlExtractorTool()

class ParseLinkRequest(BaseModel):
    url: str

@router.post("")
async def parse_product_link(req: ParseLinkRequest):
    data = await extractor.run(url=req.url)
    return {"status": "success", "product": data}
