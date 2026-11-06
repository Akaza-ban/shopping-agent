import asyncio
import sys
import os
import time

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.connection import init_db
from core.graph import ShopAIAgentWorkflow
from core.state import AgentState
from memory.session_manager import session_memory

async def run_multi_turn_test():
    await init_db()
    workflow = ShopAIAgentWorkflow()
    session_id = f"test-multiturn-{int(time.time())}"

    print(f"BẮT ĐẦU KIỂM THỬ TRÍ NHỚ ĐA LƯỢT (Session ID: {session_id})\n")

    # LƯỢT 1: Tìm kiếm sản phẩm ban đầu
    print("=" * 60)
    print("LƯỢT 1: User tìm kiếm sản phẩm")
    query_1 = "Tìm giúp tôi điện thoại iPhone tầm 20 triệu"
    print(f"User: {query_1}")

    state_1 = AgentState(session_id=session_id, user_query=query_1)
    res_1 = await workflow.execute(state_1)

    print(f"\n[AI Intent]: {res_1.intent}")
    print(f"[Số sản phẩm tìm thấy]: {len(res_1.found_products)}")
    for idx, p in enumerate(res_1.found_products[:3], 1):
        print(f"  #{idx}: {p.name} ({p.currentPrice:,.0f} đ tại {p.platformName})")
    print(f"\n[AI Trả lời Lượt 1 (trích đoạn)]: \n{res_1.final_response[:250]}...\n")

    # Chờ 1 giây để đảm bảo async commit SQLite hoàn tất
    await asyncio.sleep(1.0)

    print("=" * 60)
    print("LƯỢT 2: User hỏi tiếp nối: 'Con thứ nhất pin dùng được mấy tiếng và bảo hành thế nào?'")
    query_2 = "Con thứ nhất pin dùng được mấy tiếng và bảo hành thế nào?"
    print(f"User: {query_2}")

    state_2 = AgentState(session_id=session_id, user_query=query_2)
    res_2 = await workflow.execute(state_2)

    print(f"\n[AI Intent]: {res_2.intent} (Kỳ vọng: general_advice - KHÔNG cào mạng lại)")
    print(f"[Số sản phẩm cào mới]: {len(res_2.found_products)} (0 vì không cào lại)")
    print(f"\n[AI Trả lời Lượt 2]:\n{res_2.final_response}\n")

    # LƯỢT 3: Kiểm tra trí nhớ trong SQLite qua Session Memory
    print("=" * 60)
    print("LƯỢT 3: Kiểm tra độ bền dữ liệu trong SQLite (Persistence)")
    messages = session_memory.get_messages(session_id)
    last_prods = session_memory.get_last_products(session_id)
    print(f"Tổng số tin nhắn đã lưu: {len(messages)} (Kỳ vọng: 4 tin nhắn: 2 user + 2 ai)")
    print(f"Sản phẩm còn lưu trong session: {len(last_prods)} sản phẩm")
    for m in messages:
        print(f"  - [{m.sender.upper()}]: {m.text[:80]}...")

    assert len(messages) >= 4, "Lịch sử tin nhắn chưa được lưu đủ 4 tin"
    assert len(last_prods) > 0, "Danh sách sản phẩm lượt trước chưa được lưu"
    print("\nKIỂM THỬ TRÍ NHỚ ĐA LƯỢT THÀNH CÔNG 100%!")

if __name__ == "__main__":
    asyncio.run(run_multi_turn_test())
