.PHONY: run install test lint clean help crawl

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
	python scripts/crawl_hot.py

# Cài đặt toàn bộ thư viện cần thiết
install:
	pip install -r requirements.txt

# Chạy bộ test tự động
test:
	pytest

# Dọn dẹp cache
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

help:
	@echo "Các lệnh khả dụng:"
	@echo "  make run      - Khởi chạy server FastAPI tại http://localhost:8000 (Tự động warm-up)"
	@echo "  make crawl    - Chủ động thu thập các mặt hàng HOT vào SQLite (CLI)"
	@echo "  make install  - Cài đặt requirements.txt"
	@echo "  make test     - Chạy kiểm thử pytest"

