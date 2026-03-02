import logging
from http import HTTPStatus

from fastapi import APIRouter
from fastapi.responses import Response

from app.config import SERVICE_NAME, STUDENT
from app.db.database import check_db_connection
from app.monitoring.metrics import app_health_status, app_ready_status

healthz_router = APIRouter(prefix='/healthz', tags=['Healthz'])

@healthz_router.get('/ready')
async def ready() -> Response:
    logging.info('Readiness probe')
    if await check_db_connection():
        app_ready_status.labels(service = SERVICE_NAME, student=STUDENT).set(1)
        return Response(status_code=HTTPStatus.OK)
    app_ready_status.labels(service = SERVICE_NAME, student=STUDENT).set(0)
    return Response(status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

@healthz_router.get('/up')
async def up() -> Response:
    logging.info('Liveness probe')
    app_health_status.labels(service = SERVICE_NAME, student=STUDENT).set(1)
    return Response(status_code=HTTPStatus.OK)
