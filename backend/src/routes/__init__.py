from .chat import router as chat_router
from .products import router as products_router
from .link_parser import router as link_parser_router
from .alerts import router as alerts_router
from .crawler import router as crawler_router

__all__ = ["chat_router", "products_router", "link_parser_router", "alerts_router", "crawler_router"]

