"""Ranh giới lỗi của tầng database: SQLAlchemy chỉ được biết đến bên trong database/."""
import functools
import inspect

from sqlalchemy.exc import SQLAlchemyError

from shared.exceptions import DatabaseError


def raises_database_error(cls):
    """Mọi phương thức async công khai của repository: SQLAlchemyError -> DatabaseError.

    Bên ngoài database/ chỉ cần `except DatabaseError`, không phải import sqlalchemy.
    """
    for name, attr in list(vars(cls).items()):
        if name.startswith("_") or not inspect.iscoroutinefunction(attr):
            continue
        setattr(cls, name, _translate(attr, f"{cls.__name__}.{name}"))
    return cls


def _translate(method, label: str):
    @functools.wraps(method)
    async def wrapper(*args, **kwargs):
        try:
            return await method(*args, **kwargs)
        except SQLAlchemyError as e:
            raise DatabaseError(f"{label}: {e}") from e
    return wrapper
