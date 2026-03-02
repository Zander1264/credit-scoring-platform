from fastapi import APIRouter, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

metrics_router = APIRouter()

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status', 'service', 'student']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint', 'service', 'student'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)

app_info = Gauge(
    'app_info',
    'Application information',
    ['version', 'service', 'student']
)

app_health_status = Gauge(
    'app_health_status',
    'Application health status (1 = healthy, 0 = unhealthy)',
    ['service', 'student']
)

app_ready_status = Gauge(
    'app_ready_status',
    'Application readiness status (1 = ready, 0 = not ready)',
    ['service', 'student']
)

def init_service_metrics(service_name: str,
                         student:str,
                         version: str = '1.0.0') -> None:
    app_info.labels(service = service_name, version = version, student = student).set(1)
    app_health_status.labels(service = service_name, student=student).set(1)
    app_ready_status.labels(service = service_name, student=student).set(1)

def shutdown_service_metrics(service_name:str, student:str) -> None:
    app_health_status.labels(service = service_name, student=student).set(0)
    app_ready_status.labels(service = service_name, student=student).set(0)

@metrics_router.get('/metrics')
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
