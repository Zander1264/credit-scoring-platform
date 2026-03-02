import logging
import pytest
import pytest_asyncio

import httpx
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, Mock
from app.service import create_app
from app.api.schemas import ClientSchema
from app.redis_interact import redis_client, check_redis_connection

PIONEER_PRODUCTS = ['ConsumerLoan', 'QuickMoney', 'MicroLoan']

REPEATER_PRODUCTS = ['PrimeCredit', 'AdvantagePlus', 'LoyaltyLoan']

@pytest.fixture()
def client():
    app = create_app()
    yield TestClient(app)


@pytest.mark.parametrize('ClientSchema, expected_flow, expected_products', 
                         [
                             (ClientSchema(phone= '78945614521'), 'repeater', REPEATER_PRODUCTS),
                             (ClientSchema(phone= '78123561232'), 'pioneer', PIONEER_PRODUCTS),
                         ])
def test_get_products(ClientSchema, expected_flow, expected_products, client):
    mock_get = Mock()
    if expected_flow == 'repeater':
        mock_get.status_code = 200
        mock_get.json.return_value = REPEATER_PRODUCTS
    else:
        mock_get.status_code = 404
        mock_get.json.return_value = PIONEER_PRODUCTS
    with patch('app.api.products.check_redis_connection', return_value = False):
        with patch('httpx.AsyncClient.get', return_value = mock_get):
            response = client.post('/api/products', json=ClientSchema.model_dump())
            assert response.status_code == 200
            assert response.json() == {'flow_type': expected_flow,
                                            'available_products': expected_products}
        
def test_check_redis_connection():
    assert check_redis_connection(redis_client) == True
        
