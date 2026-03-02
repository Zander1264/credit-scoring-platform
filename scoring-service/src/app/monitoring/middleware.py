import logging
import time
import uuid
from contextvars import ContextVar
from typing import Any

from fastapi import Request

from app.monitoring.metrics import http_request_duration_seconds, http_requests_total

logger = logging.getLogger(__name__)

request_id_var: ContextVar[str] = ContextVar[str]('request_id', default='system')

def generate_request_id() -> str:
    """
    Генерирует короткий request_id в формате: a73e1a9820058365

    Использует первые 16 символов UUID без дефисов.

    Returns:
        str: 16-символьная hex строка
    """
    return uuid.uuid4().hex[:16]


async def metrics_middleware(request: Request,
                             call_next: Any,
                             service_name: str,
                             student: str) -> Any:
    """
    Middleware для сбора метрик HTTP запросов.

    Args:
        request: FastAPI Request объект
        call_next: Следующий middleware в цепочке
        service_name: Имя сервиса для метрик
    """
    request_id = request_id_var.get()
    if request_id == 'system':
        request_id = generate_request_id()
        request_id_var.set(request_id)

    extra = {'request_id': request_id}

    logger.info(
        f'Входящий запрос: {request.method} {request.url.path}',
        extra=extra
    )

    start_time = time.time()

    try:
        response = await call_next(request)
        status = response.status_code
    except Exception as e:
        logger.error(f'Ошибка обработки запроса: {e}', extra=extra, exc_info=True)
        status = 500
        raise
    finally:
        duration = time.time() - start_time

        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status=status,
            service=service_name,
            student = student
        ).inc()

        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path,
            service=service_name,
            student = student
        ).observe(duration)

        logger.info(
            f'Запрос обработан: {request.method} {request.url.path} - '
            f'status={status} duration={duration:.3f}s',
            extra=extra
        )

    return response

