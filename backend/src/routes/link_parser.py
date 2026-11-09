"""API đọc link sản phẩm. Logic nằm ở application/link.py."""

from fastapi import APIRouter, Depends

import application.link as link
from src.dependencies.rate_limit import rate_limit
from src.schemas.link import ParseLinkRequest

router = APIRouter(prefix="/parse-link", tags=["Link Parser"])


@router.post("", dependencies=[Depends(rate_limit("parse_link"))])
@router.post("/parse", dependencies=[Depends(rate_limit("parse_link"))])
async def parse_product_link(req: ParseLinkRequest):
    return await link.parse_link(req.url)
