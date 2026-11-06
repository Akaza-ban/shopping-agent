.PHONY: run install test test-unit test-integration test-live lint lint-fix format clean help crawl

# Chạy máy chủ FastAPI với Uvicorn và auto-reload
run:
	@echo "=========================================================="
	@echo " Start ShopAI Agent Backend..."
	@echo " Swagger UI Docs: http://localhost:8000/docs"
	@echo " Redoc Docs:      http://localhost:8000/redoc"
	@echo "=========================================================="
	uvicorn src.main:app --reload --host 127.0.0.1 --port 8000

# Thu thập hàng loạt dữ liệu các mặt hàng HOT vào SQLite (Phương án 1 CLI)
crawl:
	python scripts/catalog/crawl_hot.py

# Cài đặt toàn bộ thư viện cần thiết
install:
	pip install -r requirements.txt

# Chạy bộ test tự động
test:
	pytest

test-unit:
	pytest tests/unit

test-integration:
	pytest tests/integration

# Cả các test gọi trang / API thật (cần mạng và API key)
test-live:
	RUN_LIVE_TESTS=1 pytest

# Kiểm tra code (cần: pip install ruff)
lint:
	ruff check .

lint-fix:
	ruff check . --fix

format:
	ruff format .

# Dọn dẹp cache
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

help:
	@echo "Các lệnh khả dụng:"
	@echo "  make run              - Khởi chạy server FastAPI tại http://localhost:8000 (Tự động warm-up)"
	@echo "  make crawl            - Chủ động thu thập các mặt hàng HOT vào SQLite (CLI)"
	@echo "  make install          - Cài đặt requirements.txt"
	@echo "  make test             - Chạy toàn bộ test"
	@echo "  make test-unit        - Chỉ test logic (nhanh, không cần CSDL / mạng)"
	@echo "  make test-integration - Test qua API, CSDL tạm, LLM / sàn thật"
	@echo "  make test-live        - Thêm các test gọi trang / API thật"
	@echo "  make lint             - Kiểm tra code bằng ruff"
