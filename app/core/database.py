from __future__ import annotations

from typing import Any, TypeVar

from fastapi.concurrency import run_in_threadpool
from postgrest import APIResponse

T = TypeVar("T")


async def db_execute(query_builder: Any) -> APIResponse:
    """
    Выполняет запрос Supabase (Postgrest) в пуле потоков.
    Принимает объект запроса (query builder) перед вызовом .execute()
    или функцию, которая возвращает результат.
    """
    def _execute():
        # Если передан query builder (имеет метод execute)
        if hasattr(query_builder, "execute"):
            return query_builder.execute()
        # Если передана функция (callable)
        elif callable(query_builder):
            return query_builder()
        return query_builder

    return await run_in_threadpool(_execute)

