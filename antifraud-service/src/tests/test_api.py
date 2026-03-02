import pytest
import pytest_asyncio
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

from app.service import create_app
from app.api.logic import (
    score_age,
    score_employment_type,
    score_income,
    score_property_low_income,
    score_request_count,
    score_overdue_payments,
    score_profile_edit
)

@pytest.fixture
def client():
    app = create_app()
    yield TestClient(app)

@pytest.mark.parametrize('age, expected_result',
                         [
                             (18, True),
                             (17, False),
                             (19, True)
                         ])
def test_score_age(age, expected_result):
    assert score_age(age) == expected_result

@pytest.mark.parametrize('income, expected_result',
                         [
                             (10000, True),
                             (9999, False),
                             (15000, True)
                         ])
def test_score_income(income, expected_result):
    assert score_income(income) == expected_result

@pytest.mark.parametrize('emplyment_type, expected_result',
                         [
                             ('full-time', True),
                             ('unemployed', False)
                         ])
def test_score_employment_type(emplyment_type, expected_result):
    assert score_employment_type(emplyment_type) == expected_result

@pytest.mark.parametrize('property, income, expected_result',
                         [
                             (True, 29999, False),
                             (True, 30000, True),
                             (False, 29999, True),
                             (False, 30000, True)
                         ])
def test_score_property_low_income(property, income, expected_result):
    assert score_property_low_income(property, income) == expected_result

@pytest.mark.parametrize('phone_parametr, bool_parametr, ttl_parametr, request_count, '
                         f'expected_result',
                         [
                             (71234567890, True, 10000, 1, True),
                             (71234567891, False, None, None, True),
                             (71234567892, True, 10000, 3, False),
                             (71234567893, True, 10000, 2, True)
                         ])
@pytest.mark.asyncio
async def test_score_request_count(phone_parametr,
                             bool_parametr,
                             ttl_parametr,
                             request_count,
                             expected_result):
    return_value = {'name': phone_parametr, 'cache': bool_parametr,
                    'ttl': ttl_parametr, 'value': request_count}
    with patch('app.api.logic.check_redis_connection', return_value = True):
        with patch('app.api.logic.get_cache', return_value = return_value):
            with patch('app.api.logic.set_cache'):
                assert await score_request_count(phone_parametr) == expected_result

@pytest.mark.parametrize('phone_parametr, age_parametr, income_parametr, '
                         f'employment_type_parametr, property_parametr, '
                         f'antifraud_decision',
                         [
                            ('71234567890', 18, 10000, 'full-time', True, "rejected"),
                            ('71234567891', 18, 10000, 'full-time', False, "passed"),
                            ('71234567892', 17, 10000, 'full-time', False, "rejected"),
                            ('71234567893', 19, 9000, 'full-time', False, "rejected"),
                            ('71234567894', 19, 30000, 'full-time', True, "passed"),
                            ('71234567895', 19, 15000, 'unemployed', False, "rejected")
                         ])
@pytest.mark.asyncio
async def test_check_pioneer(client,
                             phone_parametr,
                             age_parametr,
                             income_parametr,
                             employment_type_parametr,
                             property_parametr,
                             antifraud_decision):
    request_data = {"user_data":
                    {
                        "phone": phone_parametr,
                        "age": age_parametr,
                        "monthly_income": income_parametr,
                        "employment_type": employment_type_parametr,
                        "has_property": property_parametr
                    }}
    with patch('app.api.antifraud.score_request_count', return_value = True):
        response = client.post('/api/antifraud/pioneer/check', json=request_data)

        assert response.status_code == 200
        assert response.json()['decision'] == antifraud_decision

@pytest.mark.parametrize('loans_history, expected_result',
                         [
                            ([{'status': 'open'},{'status': 'open'}],True),
                            ([{'status': 'closed'},{'status': 'open'}],True),
                            ([{'status': 'closed'},{'status': 'overdue'}],False)
                         ])
@pytest.mark.asyncio
async def test_score_overdue_payments(loans_history, expected_result):
    assert await score_overdue_payments(loans_history) == expected_result

@pytest.mark.parametrize('current_profile, previous_profile, expected_result',
                         [
                            ({'monthly_income': 20000, 'employment_type': 'full-time'},
                             {'monthly_income': 10000, 'employment_type': 'full-time'},
                             False),
                            ({'monthly_income': 20000, 'employment_type': 'full-time'},
                             {'monthly_income': 40000, 'employment_type': 'full-time'},
                             False),
                            ({'monthly_income': 20000, 'employment_type': 'freelance'},
                             {'monthly_income': 20000, 'employment_type': 'full-time'},
                             False),
                            ({'monthly_income': 20000, 'employment_type': 'unemployed'},
                             {'monthly_income': 20000, 'employment_type': 'full-time'},
                             False),
                            ({'monthly_income': 20000, 'employment_type': 'full-time'},
                             {'monthly_income': 20000, 'employment_type': 'full-time'},
                             True)
                         ])
@pytest.mark.asyncio
async def test_score_profile_edit(current_profile, previous_profile,expected_result):
    assert await score_profile_edit(current_profile,previous_profile) == expected_result


@pytest.fixture
def loans_history():
    return [
        {'issue_date':'2023-11-01',
         'status':'closed',
         'profile_snapshot':{
             'phone':'71234567890',
             'age':20,
             'monthly_income':30000,
             'employment_type':'full-time',
             'has_property':True
         }},
         {'issue_date':'2025-12-01',
         'status':'closed',
         'profile_snapshot':{
             'phone':'71234567890',
             'age':22,
             'monthly_income':30000,
             'employment_type':'full-time',
             'has_property':True
         }}
    ]

@pytest.mark.parametrize('age_parametr, income_parametr, '
                         f'employment_type_perametr, property_parametr,'
                         f'expected_result',
                         [
                             (22, 30000, 'full-time', True, 'passed'),
                             (22, 15000, 'full-time', True, 'rejected'),
                             (22, 70000, 'full-time', True, 'rejected'),
                             (22, 30000, 'unemployed', True, 'rejected'),
                             (22, 20000, 'full-time', False, 'passed')
                         ])
@pytest.mark.asyncio
async def test_check_repeater(client,
                              loans_history,
                              age_parametr,
                              income_parametr,
                              employment_type_perametr,
                              property_parametr,
                              expected_result):
    mock_get = Mock()
    mock_get.json.return_value = loans_history
    request_data = {'phone': '71234567890',
                     'current_profile':
                     {'age': age_parametr,
                      'monthly_income': income_parametr,
                      'employment_type': employment_type_perametr,
                      'has_property': property_parametr
                     }}
    with patch('httpx.AsyncClient.get', return_value = mock_get):
        response = client.post('/api/antifraud/repeater/check',
                                         json=request_data)
        assert response.status_code == 200
        response_json = response.json()
        assert response_json['decision'] == expected_result