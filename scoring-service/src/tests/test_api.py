import json
from typing import Generator
from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

from app.service import create_app

from datetime import datetime, UTC
from unittest.mock import AsyncMock, Mock, mock_open, patch

from app.api.logic import (
    add_product_to_history,
    find_product_by_start_index,
    score_age_pioneer,
    score_age_repeater,
    score_employment_type,
    score_history_first,
    score_history_summ_last,
    score_income,
)

from app.api.scoring import (
    PIONEER_PRODUCTS, 
    REPEATER_PRODUCTS,
    reject_json,
    repeater_scoring
)

from app.api.schemas import (
    PioneerDataSchema, 
    PioneerProductSchema, 
    RepeaterProductSchema,
    RepeaterRequestSchema
)

@pytest.fixture()
def client() -> TestClient:
    app = create_app()
    return TestClient(app)

@pytest.fixture
def repeater_user_data():
    return {
            "phone": "78945614521",
            "profile": {"age": 25,
            "monthly_income": 30000,
            "employment_type": "full_time",
            "has_property": True},
            "history": [
                {
                    "loan_id": "loan_20250101_001",
                    "product_name": "LoyaltyLoan",
                    "amount": 60000,
                    "issue_date": "2025-01-01",
                    "term_days": 120,
                    "status": "closed",
                    "close_date": "2025-04-01"
                },
                {
                    "loan_id": "loan_20250101_002",
                    "product_name": "AdvantagePlus",
                    "amount": 100000,
                    "issue_date": "2025-04-01",
                    "term_days": 180,
                    "status": "open",
                    "close_date": None
                }
            ]
        }

@pytest.fixture
def repeater_request_data():
    return {
        "phone": "78945614521",
        "products": [
    {"name": "LoyaltyLoan", "max_amount": 50000, "term_days": 60, "interest_rate_daily": 1.8},
    {"name": "AdvantagePlus", "max_amount": 120000, "term_days": 90, "interest_rate_daily": 1.6}
  ]
}

@pytest.fixture
def repeater_product():
    return RepeaterProductSchema(
        name="AdvantagePlus",
        max_amount=120000,
        term_days=90,
        interest_rate_daily=1.6
    )

@pytest.fixture
def sample_user_data_schema():
    return PioneerDataSchema(
        phone="79123456789",
        age=28,
        monthly_income=45000,
        employment_type="full_time",
        has_property=True
    )

@pytest.fixture
def sample_products_schema():
    return [
        PioneerProductSchema(name="MicroLoan", max_amount=30000, term_days=30, interest_rate_daily=2.0),
        PioneerProductSchema(name="QuickMoney", max_amount=1500000, term_days=15, interest_rate_daily=2.5)
    ]

@pytest.fixture
def sample_user_data_dict():
    return {
        "phone": "79123456789",
        "age": 28,
        "monthly_income": 45000,
        "employment_type": "full_time",
        "has_property": True
    }

@pytest.fixture
def sample_products_dict():
    return [
        {"name": "MicroLoan", "max_amount": 30000, "term_days": 30, "interest_rate_daily": 2.0},
        {"name": "QuickMoney", "max_amount": 1500000, "term_days": 15, "interest_rate_daily": 2.5}
    ]

def test_score_age():
    assert score_age_pioneer(20) == 1
    assert score_age_pioneer(35) == 3
    assert score_age_pioneer(60) == 2

def test_score_income():
    assert score_income(15000) == 1
    assert score_income(30000) == 2
    assert score_income(29999) == 1
    assert score_income(50000) == 3

def test_score_employment_type():
    assert score_employment_type('full_time') == 3
    assert score_employment_type('freelance') == 1
    assert score_employment_type('unemployed') == 0

def test_find_product_by_start_index(sample_products_schema):
    product = find_product_by_start_index(sample_products_schema, PIONEER_PRODUCTS, start_index=1)
    assert product.name == "QuickMoney"

    product = find_product_by_start_index(sample_products_schema, PIONEER_PRODUCTS, start_index=2)
    assert product.name == "MicroLoan"

    product = find_product_by_start_index([], PIONEER_PRODUCTS, start_index=len(PIONEER_PRODUCTS)-1)
    assert product is None

def test_pioneer_scoring_reject_case(sample_user_data_dict, sample_products_dict, client):
    # Проверяем случай отказа (низкий доход)
    low_income_user_data = {"phone":"79123456789", "age":28, "monthly_income":9000, "employment_type":"full_time", "has_property":True}
    mock_get = Mock()
    mock_get.json.return_value = {
            "profile":{
            "age": 25,
            "monthly_income": 9000,
            "employment_type": "full_time",
            "has_property": True},
            "history": [
                {
                    "loan_id": "loan_20250101_001",
                    "product_name": "LoyaltyLoan",
                    "amount": 60000,
                    "issue_date": "2025-01-01",
                    "term_days": 120,
                    "status": "closed",
                    "close_date": "2025-04-01"
                },
                {
                    "loan_id": "loan_20250101_002",
                    "product_name": "AdvantagePlus",
                    "amount": 100000,
                    "issue_date": "2025-04-01",
                    "term_days": 180,
                    "status": "open",
                    "close_date": None
                }
            ]
        }
    mock_get.status_code = 200
    mock_post = Mock()
    mock_post.status_code = 200
    mock_post.json.return_value = {"decision": "rejected"}
    with patch('httpx.AsyncClient.post', return_value = mock_post):
        response = client.post("/api/scoring/pioneer", json={"user_data":low_income_user_data, "products":sample_products_dict})
    assert response.status_code == 200
    assert response.json() == reject_json

    # Проверяем отказ (продукт отсутствует)

    no_products_response = client.post("/api/scoring/pioneer", json={"user_data":sample_user_data_dict, "products":[]})
    assert no_products_response.status_code == 200
    assert no_products_response.json() == reject_json

def test_pioneer_scoring_accepted_cases(sample_user_data_dict, sample_products_dict, client):
    # Положительный случай (соответствие условиям выдачи займа)
    with patch('app.api.scoring.KafkaProducer', new_callable=AsyncMock) as mock_kafka_producer:
        client.app.state.producer = mock_kafka_producer.return_value
        mock_kafka_producer.return_value.send = AsyncMock(return_value=None)
        mock_post = Mock()
        mock_post.status_code = 200
        mock_post.json.return_value = {"decision": "passed"}
        with patch('httpx.AsyncClient.post', return_value = mock_post):
            response = client.post("/api/scoring/pioneer", json={"user_data":sample_user_data_dict, "products":sample_products_dict})
        assert response.status_code == 200
        assert response.json()["decision"] == "accepted"


    # Другой позитивный случай (другой профиль заемщика)
    with patch('app.api.scoring.KafkaProducer', new_callable=AsyncMock) as mock_kafka_producer:
        another_user_data = {"phone":"79123456789", "age":35, "monthly_income":50000, "employment_type":"frelance", "has_property":False}
        client.app.state.producer = mock_kafka_producer.return_value
        mock_kafka_producer.return_value.send = AsyncMock(return_value=None)
        mock_post = Mock()
        mock_post.status_code = 200
        mock_post.json.return_value = {"decision": "passed"}
        with patch('httpx.AsyncClient.post', return_value = mock_post):
            response = client.post("/api/scoring/pioneer", json={"user_data":another_user_data, "products":sample_products_dict})
        assert response.status_code == 200
        assert response.json()["decision"] == "accepted"


def test_score_age_repeater():
    assert score_age_repeater(20) == 2
    assert score_age_repeater(21) == 1
    assert score_age_repeater(25) == 1
    assert score_age_repeater(26) == 3
    assert score_age_repeater(40) == 3
    assert score_age_repeater(41) == 2
    assert score_age_repeater(50) == 2

def test_score_history_summ_last():
    history = [{"amount": 49999}]
    assert score_history_summ_last(history) == 1
    
    history = [{"amount": 75000}]
    assert score_history_summ_last(history) == 2
    
    history = [{"amount": 150000}]
    assert score_history_summ_last(history) == 3
    
def test_score_history_first(repeater_user_data):
    assert score_history_first(repeater_user_data['history']) == 0

def test_add_product_to_history(repeater_product):
    
    result = add_product_to_history(repeater_product)
    assert result['product_name'] == 'AdvantagePlus'
    assert result['amount'] == 120000
    assert result['term_days'] == 90
    assert result['status'] == 'open'
    assert result['close_date'] is None

    with patch('app.api.logic.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime(2025, 5, 5, tzinfo=UTC)
        result = add_product_to_history(repeater_product)
        assert result['issue_date'] == '2025-05-05'

def test_reapeter_scoring_not_found(client):
    mock_get = Mock()
    mock_get.status_code = 404
    with patch('httpx.Client.get', return_value=mock_get):
        response = client.get("/api/scoring/repeater?phone=79123456780")
        assert response.status_code == 404

def test_repeater_scoring_accepted_case(repeater_user_data, repeater_request_data, client):
    mock_get = Mock()
    mock_get.status_code = 200
    mock_get.json.return_value = repeater_user_data

    mock_post = Mock()
    mock_post.status_code = 200
    mock_post.json.return_value = {"decision": "passed"}

    with patch('httpx.AsyncClient.get', return_value=mock_get):
        with patch('httpx.AsyncClient.post', return_value=mock_post):
            with patch('app.api.scoring.KafkaProducer', new_callable=AsyncMock) as mock_kafka_producer:
                client.app.state.producer = mock_kafka_producer.return_value
                mock_kafka_producer.return_value.send = AsyncMock(return_value=None)
                response = client.post("/api/scoring/repeater", json=repeater_request_data)
                assert response.status_code == 200
