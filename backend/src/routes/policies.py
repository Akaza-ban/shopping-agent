"""API tra cứu chính sách đổi trả, bảo hành. Logic nằm ở application/policies.py."""
from fastapi import APIRouter, Query

import application.policies as policies
from src.schemas.policies import LookupRequest

router = APIRouter(prefix="/policies", tags=["Policies"])


@router.get("")
async def list_policies(platforms: str = Query("", description="Mã nền tảng, phân tách bằng dấu phẩy; trống = tất cả"),
                        category: str = "all"):
    ids = [p for p in platforms.split(",") if p] or None
    return await policies.list_policies(ids, category)


@router.post("/lookup")
async def lookup_policies(req: LookupRequest):
    return await policies.lookup(req.query.strip(), req.platform_ids, req.category, req.language,
                                 req.product_platform_ids or None, req.scenario)
