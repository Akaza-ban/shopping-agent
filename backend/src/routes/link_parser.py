"""API đọc link sản phẩm. Logic nằm ở application/link.py."""
from fastapi import APIRouter

import application.link as link
from src.schemas.link import ParseLinkRequest

router = APIRouter(prefix="/parse-link", tags=["Link Parser"])


@router.post("")
@router.post("/parse")
async def parse_product_link(req: ParseLinkRequest):
    return await link.parse_link(req.url)
