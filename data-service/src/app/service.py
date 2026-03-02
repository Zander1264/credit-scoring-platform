import argparse
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import uvicorn
from aiokafka.errors import KafkaError
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import main_router
from app.config import SERVICE_NAME, STUDENT, Config, KafkaConfig, set_config
from app.consumer import KafkaConsumer
from app.healthz import healthz_router
from app.monitoring.metrics import (
    init_service_metrics,
    metrics_router,
    shutdown_service_metrics,
)
from app.monitoring.middleware import metrics_middleware
from app.monitoring.tracing import instrument_fastapi, instrument_httpx, setup_tracing


def check_log_files_and_folders(project_name: str, module_name: str) -> str:
    root_dir = Path.cwd().parent
    log_dir = root_dir / 'logs'
    project_log_dir = log_dir / project_name
    log_file_name = f'{module_name}.log'
    full_log_path = project_log_dir / log_file_name

    project_log_dir.mkdir(parents=True, exist_ok=True)

    return str(full_log_path)

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any) -> Any:
        return await metrics_middleware(request, call_next,
                                        service_name= SERVICE_NAME,
                                        student= STUDENT)

@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Запускает и останавливает приложение."""
    logging.info('Starting the service')

    setup_tracing(f'{SERVICE_NAME}-{STUDENT}')
    instrument_httpx()

    init_service_metrics(f'{SERVICE_NAME}', f'{STUDENT}')

    config = Config()
    kafka_config = KafkaConfig(
        url=config.kafka_url,
        request_timeout_ms=config.kafka_timeout_ms,
        retry_timeout_ms=config.kafka_retry_timeout_ms,
        topic=config.kafka_topic,
    )

    # Инициализация consumer
    app.state.consumer = KafkaConsumer(kafka_config)
    await app.state.consumer.start()
    while not await app.state.consumer.is_connected():
        try:
            await app.state.consumer.start()
        except KafkaError:
            logging.error('Kafka unavailable. Retrying...')
        await asyncio.sleep(5)

    yield

    logging.info('Shutting down...')
    if hasattr(app.state, 'consumer'):
        await app.state.consumer.stop()
    shutdown_service_metrics(service_name=SERVICE_NAME, student=STUDENT)


def create_app() -> FastAPI:
    app = FastAPI(
        title='Data Service',
        openapi_url='/openapi.json',
        lifespan=lifespan
    )
    app.include_router(main_router)
    app.include_router(healthz_router)
    app.include_router(metrics_router)

    app.add_middleware(MetricsMiddleware)

    return app


if __name__ == '__main__':
    log_file_path = check_log_files_and_folders(SERVICE_NAME, __name__)
    file_handler = logging.FileHandler(log_file_path)
    console_handler = logging.StreamHandler()
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s - %(levelname)s] %(name)s: %(message)s',
        handlers=[file_handler, console_handler],
    )

    logger = logging.getLogger(__name__)
    logger.propagate = True

    parser = argparse.ArgumentParser(description='Data Service')
    parser.add_argument('--config', default='config.yaml')
    args = parser.parse_args()
    os.environ['CONFIG_PATH'] = args.config

    config = set_config('app')
    app = create_app()

    instrument_fastapi(app)

    uvicorn.run(
        app,
        host=config['host'],
        port=config['port'],
        log_config=None
    )
