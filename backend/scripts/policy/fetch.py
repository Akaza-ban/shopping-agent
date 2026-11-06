import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from sqlalchemy import text  # noqa: E402

from database.connection import close_db, engine, init_db  # noqa: E402
from database.repositories import policy_repository  # noqa: E402
from services.policy.fetcher import fetch_all  # noqa: E402
from services.policy.service import ensure_seeded  # noqa: E402


async def main(platform_ids):
    await init_db()
    async with engine.begin() as conn:
        await conn.execute(text(
            "UPDATE policy_documents SET doc_type = 'summary' WHERE doc_type = 'return' AND url IN "
            "(SELECT home_url FROM platforms WHERE platforms.id = policy_documents.platform_id)"))
    await ensure_seeded()

    results = await fetch_all(platform_ids or None)
    for pid, docs in results.items():
        for d in docs:
            if "error" in d:
                print(f"[{pid}] LỖI {d['url']}: {d['error']}")
                continue
            changed = await policy_repository.upsert_document(pid, d["doc_type"], d["title"], d["url"], d["chunks"])
            print(f"[{pid}] {'cập nhật' if changed else 'không đổi'}: {len(d['chunks'])} đoạn, "
                  f"{sum(len(c) for c in d['chunks'])} ký tự - {d['url']}")

    print("\nKho tài liệu chính sách:")
    for doc in await policy_repository.list_documents():
        print(f"  {doc['platformId']:<11} {doc['docType']:<8} {doc['chunks']:>3} đoạn {doc['chars']:>6} ký tự  {doc['url']}")
    await close_db()

if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
