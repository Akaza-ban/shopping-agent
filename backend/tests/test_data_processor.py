import sys
import pytest

sys.path.insert(0, ".")

from services.catalog.data_processor import data_processor

def test_clean_title_removes_promotional_noise():
    """Kiểm tra Khâu 1: Làm sạch tiêu đề, loại bỏ các từ rác quảng cáo."""
    raw_title = "[Mẫu mới 2024] [Chính hãng VN/A] Điện thoại Apple iphone 15 Pro Max 256GB - Bảo hành 12 tháng"
    clean = data_processor.clean_title(raw_title)

    # Đã loại bỏ các tag rác [Mẫu mới...], [Chính hãng...], viết hoa chuẩn Apple, iPhone
    assert "Mẫu mới" not in clean
    assert "VN/A" not in clean
    assert "Bảo hành" not in clean
    assert "Apple" in clean
    assert "256GB" in clean
    clean_asc = clean.encode('ascii', 'ignore').decode()
    print(f"\n[Title Cleaning]: Clean Title -> {clean_asc}")


def test_normalize_price_and_discount():

    """Kiểm tra Khâu 2: Chuẩn hóa giá tiền và tính toán phần trăm giảm giá chuẩn."""
    # Trường hợp 1: Giá gốc bằng 0 hoặc thấp hơn giá bán do web lỗi
    curr, orig, disc = data_processor.normalize_price_and_discount(19490000, 0)
    assert curr == 19490000.0
    assert orig == 19490000.0
    assert disc == 0

    # Trường hợp 2: Giá có giảm thực tế
    curr2, orig2, disc2 = data_processor.normalize_price_and_discount(20000000, 25000000)
    assert curr2 == 20000000.0
    assert orig2 == 25000000.0
    assert disc2 == 20  # Giảm đúng 20%

    # Trường hợp 3: Giá chuỗi có ký tự đặc biệt '15.990.000₫'
    curr3, orig3, disc3 = data_processor.normalize_price_and_discount("15.990.000₫", "19.990.000₫")
    assert curr3 == 15990000.0
    assert orig3 == 19990000.0
    assert disc3 == 20

def test_clean_url_and_image():
    """Kiểm tra Khâu 3: Cắt bỏ query params rác và bù protocol https cho ảnh."""
    raw_url = "https://tiki.vn/dien-thoai-iphone-15-p12345.html?spid=67890&utm_source=google&utm_campaign=sale"
    raw_img = "//cdn.tgdd.vn/Products/Images/42/305658/iphone-15-thumb.jpg"

    clean_url, clean_img = data_processor.clean_url_and_image(raw_url, raw_img)

    assert "utm_source" not in clean_url
    assert "spid" not in clean_url
    assert clean_url == "https://tiki.vn/dien-thoai-iphone-15-p12345.html"
    assert clean_img.startswith("https://")

def test_structure_specs():
    """Kiểm tra Khâu 4: Cấu trúc hóa thông số kỹ thuật thành dictionary key-value."""
    raw_specs = 'Màn hình 6.7" - Chip Apple A17 Pro - RAM 8 GB'
    product_name = "iPhone 15 Pro Max 256GB"

    specs = data_processor.structure_specs(raw_specs, product_name)

    assert isinstance(specs, dict)
    assert "Màn hình" in specs
    assert "Chip / CPU" in specs
    assert "RAM" in specs
    # Tự động trích xuất thêm bộ nhớ 256GB từ tên sản phẩm
    assert "Bộ nhớ / Ổ cứng" in specs
    assert "256GB" in specs["Bộ nhớ / Ổ cứng"]
    print(f"\n[Structured Specs]: {len(specs)} attributes parsed successfully")

def test_full_pipeline_process_product_list():

    """Kiểm tra chạy toàn bộ pipeline danh sách sản phẩm và chống trùng lặp."""
    raw_products = [
        {
            "id": "1",
            "name": "[Chính hãng] Laptop Asus Vivobook 15 i5 16GB RAM 512GB SSD",
            "currentPrice": "15.490.000₫",
            "originalPrice": "18.490.000₫",
            "rating": 4.85,
            "reviewsCount": "120 đánh giá",
            "brand": "Asus",
            "image": "//cdn.tgdd.vn/laptop.jpg",
            "externalUrl": "https://thegioididong.com/laptop/asus?utm_source=fb"
        },

        # Bản ghi trùng lặp
        {
            "id": "1-duplicate",
            "name": "[Chính hãng] Laptop Asus Vivobook 15 i5 16GB RAM 512GB SSD",
            "currentPrice": "15.490.000₫",
            "originalPrice": "18.490.000₫",
            "externalUrl": "https://thegioididong.com/laptop/asus?utm_source=google"
        },
        # Bản ghi lỗi giá <= 0
        {
            "id": "2",
            "name": "Sản phẩm lỗi giá",
            "currentPrice": 0,
            "originalPrice": 0
        }
    ]

    cleaned_list = data_processor.process_product_list(raw_products)

    # Chỉ còn 1 sản phẩm hợp lệ duy nhất (loại bản ghi lỗi và loại bản ghi trùng URL)
    assert len(cleaned_list) == 1
    item = cleaned_list[0]
    assert item["name"] == "Laptop Asus Vivobook 15 i5 16GB RAM 512GB SSD"
    assert item["currentPrice"] == 15490000.0
    assert item["originalPrice"] == 18490000.0
    assert item["discountPercent"] == 16
    assert item["image"].startswith("https://")
    assert "utm_source" not in item["externalUrl"]
    assert item["brand"] == "Asus"

if __name__ == "__main__":
    print("=== TEST DATA CLEANING & NORMALIZATION PIPELINE ===")
    test_clean_title_removes_promotional_noise()
    print(" [OK] 1. Title sanitization verified")
    test_normalize_price_and_discount()
    print(" [OK] 2. Price and discount validation verified")
    test_clean_url_and_image()
    print(" [OK] 3. URL and image normalization verified")
    test_structure_specs()
    print(" [OK] 4. Specs structuring & extraction verified")
    test_full_pipeline_process_product_list()
    print(" [OK] 5. Full pipeline & deduplication verified")
    print("\n=== ALL DATA PROCESSING TESTS PASSED 100%! ===")
