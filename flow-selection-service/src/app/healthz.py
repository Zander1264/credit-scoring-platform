import logging
from http import HTTPStatus

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.config import SERVICE_NAME, STUDENT, set_config
from app.monitoring.metrics import app_health_status, app_ready_status
from app.redis_interact import check_redis_connection, redis_client

healthz_router = APIRouter(prefix='/healthz', tags=['Healthz'])

@healthz_router.get('/ready')
async def ready() -> Response:
    config = set_config('data_service')
    base_url = config['base_url']
    try:
        if check_redis_connection(redis_client):
            logging.info('Redis is connected')
            async with httpx.AsyncClient(
                timeout=config['timeout'],
                base_url=base_url) as async_client:
                response = await async_client.get('/healthz/ready')
                if response.status_code == 200:
                    logging.info('Data service is ready')
                    app_ready_status.labels(service = SERVICE_NAME,
                                            student=STUDENT).set(1)
                    return Response(status_code=HTTPStatus.OK)
    except HTTPException as e:
        logging.error(f'Can`t connect to data-service: {e}')
        app_ready_status.labels(service = SERVICE_NAME, student=STUDENT).set(0)
        return Response(status_code=HTTPStatus.NOT_FOUND)
    except Exception as e:
        logging.error(f'Unknown error: {e}')
        app_ready_status.labels(service = SERVICE_NAME, student=STUDENT).set(0)
        return Response(status_code=HTTPStatus.INTERNAL_SERVER_ERROR)
    app_ready_status.labels(service = SERVICE_NAME, student=STUDENT).set(0)
    return Response(status_code=HTTPStatus.INTERNAL_SERVER_ERROR)


@healthz_router.get('/up')
async def up() -> Response:
    logging.info('Liveness probe')
    app_health_status.labels(service = SERVICE_NAME, student=STUDENT).set(1)
    return Response(status_code=200)
