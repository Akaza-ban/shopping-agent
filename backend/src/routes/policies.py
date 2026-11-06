from typing import List, Literal, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from database.repositories import policy_repository
from services.policy import service as policy_service

router = APIRouter(prefix="/policies", tags=["Policies"])


class LookupRequest(BaseModel):
    query: str = Field("", max_length=300)
    platform_ids: List[str] = Field(default_factory=list)
    category: str = "all"
    language: Literal["vi", "en"] = "vi"
    product_platform_ids: List[str] = Field(default_factory=list)
    scenario: Optional[Literal["defect", "change_mind", "wrong_item", "warranty"]] = None


@router.get("")
async def list_policies(platforms: str = Query("", description="Mã nền tảng, phân tách bằng dấu phẩy; trống = tất cả"),
                        category: str = "all"):
    ids = [p for p in platforms.split(",") if p] or None
    return await policy_repository.list_policies(ids, category)


@router.post("/lookup")
async def lookup_policies(req: LookupRequest):
    return await policy_service.lookup(req.query.strip(), req.platform_ids, req.category, req.language,
                                       req.product_platform_ids or None, req.scenario)
