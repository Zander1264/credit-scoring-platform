import logging
from logging import getLogger

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.api.schemas import ClientSchema
from app.config import set_config
from app.monitoring.tracing import get_tracer
from app.redis_interact import cached_get_products, check_redis_connection, redis_client

products_router = APIRouter()

tracer = get_tracer()

flow_logger = getLogger(__name__)

config = set_config('data_service')

@products_router.post('/products',
                      tags=['Products'],
                      summary='Посмотреть список доступных продуктов')
async def get_products(client: ClientSchema) -> JSONResponse:
    with tracer.start_as_current_span('get_products'):
        base_url = config['base_url']
        phone = client.phone
        repeater = False
        async with httpx.AsyncClient(
            timeout=config['timeout'],
            base_url=base_url) as async_client:
            if check_redis_connection(redis_client):
                client_data = await cached_get_products(redis_client,
                                                phone,
                                                async_client,
                                                f'/user-data?phone={phone}')
                logging.info(client_data)
                logging.info(client_data['response']['status_code'])
                if client_data['response']['status_code'] == 200:
                    repeater = True
                if client_data['response']['status_code'] == 404:
                    repeater = False
            else:
                try:
                    response = await async_client.get(f'/user-data?phone={phone}')

                    if response.status_code == 200:
                        repeater = True
                    if response.status_code == 404:
                        repeater = False
                    if response.status_code >= 500:
                        flow_logger.error(f'Server error: {response.status_code}')
                        raise HTTPException(status_code=502, detail='Server error')
                except httpx.RequestError as err:
                    flow_logger.error(f'Server error: {err}')
                    raise RuntimeError('Server error') from err
            if check_redis_connection(redis_client):
                flow_type = 'repeater' if repeater else 'pioneer'
                products_data = await cached_get_products(redis_client,
                                                    flow_type,
                                                    async_client,
                                                    f'/api/products?flow_type={flow_type}')
                products = products_data['response']['json']
                return JSONResponse(status_code=200, content={'flow_type': flow_type,
                        'available_products': products})
            flow_type = 'repeater' if repeater else 'pioneer'
            try:
                response = await async_client.get(
                    f'/api/products?flow_type={flow_type}')
                products = response.json()
                return JSONResponse(status_code=200, content={
                    'flow_type': flow_type,
                    'available_products': products
                })
            except httpx.RequestError as err:
                flow_logger.error(f'Server error: {err}')
                raise RuntimeError('Server error') from err
            except Exception as err:
                flow_logger.error(f'Unexpected error: {err}')
                raise
