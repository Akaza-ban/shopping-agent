"""Cấu hình log chung: một định dạng cho mọi logger của ứng dụng."""
import logging

LOG_FORMAT = "%(asctime)s %(levelname)-7s [%(name)s] %(message)s"
NOISY_LOGGERS = ("httpx", "httpcore", "chromadb", "openai")


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(level=level, format=LOG_FORMAT)
    for name in NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
