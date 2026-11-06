import asyncio
import json
import sys
import os

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath("."))

async def test_sse_streaming():
    print("[Test SSE Streaming] Bắt đầu kiểm thử Server-Sent Events...")
    
    from core.state import AgentState
    from core.graph import ShopAIAgentWorkflow
    
    workflow = ShopAIAgentWorkflow()
    state = AgentState(
        session_id="test-sse-session-001",
        user_query="Tìm điện thoại tầm 15 đến 20 triệu"
    )
    
    events_received = []
    tokens = []
    products_count = 0
    suggestions = []
    
    print("\nĐang lắng nghe luồng SSE stream:")
    print("-" * 50)
    
    async for event_item in workflow.execute_stream(state):
        evt_type = event_item["event"]
        evt_data = event_item["data"]
        events_received.append(evt_type)
        
        if evt_type == "status":
            print(f"[STATUS] {evt_data.get('stage')}: {evt_data.get('message')}")
        elif evt_type == "products":
            products_count = evt_data.get("count", 0)
            print(f"[PRODUCTS] Đã nhận {products_count} sản phẩm cho thẻ card UI!")
            for idx, p in enumerate(evt_data.get("items", []), 1):
                print(f"   {idx}. {p['name']} | Giá: {p['currentPrice']:,.0f} đ | {p['platformName']}")
        elif evt_type == "token":
            tok = evt_data.get("content", "")
            tokens.append(tok)
            # In realtime ra console
            print(tok, end="", flush=True)
        elif evt_type == "suggestions":
            suggestions = evt_data
            print("\n[SUGGESTIONS] Gợi ý câu hỏi tiếp theo:")
            for s in suggestions:
                print(f"   - {s}")
        elif evt_type == "done":
            print(f"\n[DONE] Hoàn tất stream cho session: {evt_data.get('session_id')}")

    print("\n" + "=" * 50)
    print("KẾT QUẢ TEST SSE STREAMING:")
    print(f"- Các loại sự kiện nhận được: {set(events_received)}")
    print(f"- Số lượng token đã stream: {len(tokens)}")
    print(f"- Số sản phẩm tìm thấy: {products_count}")
    print(f"- Số gợi ý tiếp theo: {len(suggestions)}")
    
    assert "status" in events_received, "Thiếu sự kiện status"
    assert "token" in events_received, "Thiếu sự kiện token"
    assert "done" in events_received, "Thiếu sự kiện done"
    assert len(tokens) > 0, "Không nhận được token nào"
    assert len(suggestions) > 0, "Không nhận được gợi ý nào"
    print("TEST SSE STREAMING THÀNH CÔNG RỰC RỠ!")

if __name__ == "__main__":
    asyncio.run(test_sse_streaming())
