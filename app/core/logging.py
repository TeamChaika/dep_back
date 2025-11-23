from __future__ import annotations

import logging
import sys
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger("api")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Генерируем request_id для отслеживания запроса
        request_id = request.headers.get("X-Request-ID", str(time.time()))
        
        # Логируем входящий запрос
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"| IP: {request.client.host if request.client else 'unknown'} "
            f"| Request-ID: {request_id}"
        )

        try:
            response = await call_next(request)
            
            # Вычисляем время выполнения
            process_time = (time.time() - start_time) * 1000
            
            # Логируем успешный ответ
            logger.info(
                f"Response: {response.status_code} "
                f"| Time: {process_time:.2f}ms "
                f"| Request-ID: {request_id}"
            )
            
            return response
            
        except Exception as e:
            # Логируем необработанные ошибки
            process_time = (time.time() - start_time) * 1000
            logger.error(
                f"Error: {str(e)} "
                f"| Time: {process_time:.2f}ms "
                f"| Request-ID: {request_id}",
                exc_info=True
            )
            raise


def setup_logging():
    """Настройка логирования для всего приложения"""
    
    # Формат логов
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Настраиваем корневой логгер
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),  # Вывод в stdout для Docker
        ]
    )
    
    # Настраиваем логгер приложения
    app_logger = logging.getLogger("api")
    app_logger.setLevel(logging.INFO)
    
    # Убираем лишние логи от uvicorn, если нужно (оставляем только ошибки)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

