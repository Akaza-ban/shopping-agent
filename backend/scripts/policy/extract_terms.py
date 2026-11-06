import asyncio
import json
import os
import sys
from datetime import datetime

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BACKEND_DIR)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from database.connection import close_db, init_db  # noqa: E402
from database.repositories import policy_repository  # noqa: E402
from services.policy.extractor import extract_terms  # noqa: E402

DRAFT = os.path.join(BACKEND_DIR, "docs", "policy_terms_draft.json")
TERM_KEYS = ("return_window_days", "free_return", "return_conditions", "return_shipping_fee", "refund_time",
             "defect_exchange", "warranty_handling", "exceptions")


async def draft():
    drafts = []
    for doc in await policy_repository.official_documents():
        try:
            terms = await extract_terms(doc["platformName"], doc["content"])
        except Exception as e:
            print(f"[{doc['platformId']}] LỖI: {e}")
            continue
        drafts.append({"platform_id": doc["platformId"], "document_id": doc["id"], "source_url": doc["url"],
                       "fetched_at": doc["fetchedAt"].strftime("%Y-%m-%d") if doc["fetchedAt"] else None, **terms})
        warn = f" | số không thấy trong trang: {terms['unsupported_numbers']}" if terms["unsupported_numbers"] else ""
        print(f"[{doc['platformId']}] {terms['return_window_days']} ngày, trả miễn phí: {terms['free_return']}{warn}")
    os.makedirs(os.path.dirname(DRAFT), exist_ok=True)
    with open(DRAFT, "w", encoding="utf-8") as f:
        json.dump(drafts, f, ensure_ascii=False, indent=2)
    print(f"\nĐã ghi bản nháp: {DRAFT}\nDuyệt xong chạy lại với --apply để ghi vào CSDL.")


async def apply():
    with open(DRAFT, encoding="utf-8") as f:
        drafts = json.load(f)
    for d in drafts:
        checked = datetime.strptime(d["fetched_at"], "%Y-%m-%d") if d.get("fetched_at") else None
        await policy_repository.upsert_terms(d["platform_id"], {k: d[k] for k in TERM_KEYS},
                                             document_id=d.get("document_id"), last_checked=checked)
        print(f"[{d['platform_id']}] đã ghi điều khoản")


async def main(do_apply: bool):
    await init_db()
    await (apply() if do_apply else draft())
    await close_db()


if __name__ == "__main__":
    asyncio.run(main("--apply" in sys.argv[1:]))
