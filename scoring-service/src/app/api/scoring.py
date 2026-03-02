import logging
from datetime import UTC, datetime, timedelta
from logging import getLogger

import httpx
from aiokafka.errors import KafkaError
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.logic import (
    find_product_by_start_index,
    score_age_pioneer,
    score_age_repeater,
    score_employment_type,
    score_history_first,
    score_history_summ_last,
    score_income,
)
from app.api.schemas import (
    PioneerDataSchema,
    PioneerProductSchema,
    RepeaterRequestSchema,
)
from app.config import set_config
from app.monitoring.tracing import get_tracer
from app.producer import KafkaProducer

scoring_logger = getLogger(__name__)

tracer = get_tracer()

scoring_router = APIRouter(prefix='/scoring')

reject_json: dict[str, str|list[None]] = {'decision': 'rejected',
               'product': []}

PIONEER_PRODUCTS = ['ConsumerLoan', 'QuickMoney', 'MicroLoan']

REPEATER_PRODUCTS = ['PrimeCredit', 'AdvantagePlus', 'LoyaltyLoan']

antifraud_config = set_config('antifraud_service')
data_service_config = set_config('data_service')

@scoring_router.post('/pioneer', tags=['Scoring'], summary='Скоринг нового клиента')
async def pioneer_scoring(user_data: PioneerDataSchema,
                    products: list[PioneerProductSchema],
                    request: Request) -> JSONResponse:
    with tracer.start_as_current_span('pioneer_scoring'):
        if len(products) == 0:
            return JSONResponse(status_code=200,
                                content=reject_json)

        async with httpx.AsyncClient(base_url=antifraud_config['base_url'],
                               timeout=antifraud_config['timeout']) as async_client:
            response_antifraud = await async_client.post('/api/antifraud/pioneer/check',
                                               content=user_data.model_dump())
            if response_antifraud.json()['decision'] == 'rejected':
                return JSONResponse(status_code=200, content=reject_json)

        score = 0
        score+=score_age_pioneer(user_data.age)

        score+=score_income(user_data.monthly_income)

        score+=score_employment_type(user_data.employment_type)

        if user_data.has_property:
            score+=2

        match score:
            case score if score <= 4:
                return JSONResponse(status_code=200, content=reject_json)
            case score if 5 <= score <= 6:
                product_name = 'MicroLoan'
            case score if 7 <= score <= 8:
                product_name = 'QuickMoney'
            case _:
                product_name = 'ConsumerLoan'

        product = find_product_by_start_index(products,
                                            PIONEER_PRODUCTS,
                                            start_index=PIONEER_PRODUCTS.index(product_name))

        if product is None:
            return JSONResponse(status_code=200, content=reject_json)
        current_time = datetime.now(UTC).strftime('%Y%m%d%H%M%S')
        kafka_message = {
            'version': 1,
            'occurred_at': datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]+'Z',
            'phone': user_data.phone,
            'event': 'pioneer_accepted',
            'profile': {
                'age': user_data.age,
                'monthly_income': user_data.monthly_income,
                'employment_type': user_data.employment_type,
                'has_property': user_data.has_property
            },
            'history_entry': {
                'loan_id': f'loan_{user_data.phone}_{current_time}',
                'product_name': product_name,
                'amount': product.max_amount,
                'issue_date': datetime.now(UTC).strftime('%Y-%m-%d'),
                'term_days': product.term_days,
                'status': 'open',
                'close_date': None
            }
        }
        producer: KafkaProducer = request.app.state.producer
        try:
            await producer.send(message=kafka_message,
                                key=user_data.phone)
        except KafkaError as kafka_error:
            scoring_logger.error(f'Error: {kafka_error}'
                                f'Phone: {user_data.phone}')
        scoring_logger.info(msg = {'decision': 'accepted',
                                'product': product.model_dump()})
        return JSONResponse(status_code=200,
                            content={'decision': 'accepted',
                                    'product': product.model_dump()})

@scoring_router.post('/repeater', tags=['Scoring'], summary='Скоринг старого клиента')
async def repeater_scoring(request_body: RepeaterRequestSchema,
                     request: Request) -> JSONResponse:
    with tracer.start_as_current_span('repeater_scoring'):
        base_data_url = data_service_config['base_url']
        # начало первичных проверок
        async with httpx.AsyncClient(base_url=base_data_url,
                        timeout=data_service_config['timeout']) as client:
            try:
                get_response = await client.get(
                    f'/user-data?phone={request_body.phone}')
            except Exception as err:
                scoring_logger.error(f'Error: {err}'
                                    f'Endpoint: /repeater.')
                raise HTTPException(status_code=502) from err

            if get_response.status_code == 404:
                scoring_logger.warning(f'User not found: {request_body.phone}')
                raise HTTPException(status_code=404, detail='User not found')
            if get_response.status_code >= 500:
                scoring_logger.warning(f'Server error: {get_response.status_code}')
                raise HTTPException(status_code=502,
                                        detail='Server error')
            if get_response.status_code == 200:

                client_data = get_response.json()
                history = client_data['history']
                client_data = client_data['profile']
                score = 0

                async with httpx.AsyncClient(base_url=antifraud_config['base_url'],
                                             timeout=antifraud_config['timeout']
                                             ) as async_client_antifraud:
                    try:
                        request_content = {'phone': request_body.phone,
                                     'current_profile': client_data}
                        response_antifraud = await async_client_antifraud.post(
                            '/api/antifraud/repeater/check',
                            json=request_content)
                        if response_antifraud.json()['decision'] == 'rejected':
                            return JSONResponse(status_code=200, content=reject_json)
                    except HTTPException as http_error:
                        logging.error(f'HTTP error: {http_error}')
                        raise HTTPException(status_code=502) from http_error
                    except Exception as err:
                        logging.error(f'Unknow server error: {err}')
                        raise HTTPException(status_code=502) from err

                history.sort(key=lambda x: x['issue_date'], reverse=False)

                if (datetime.strptime(history[0]['issue_date'],
                                    '%Y-%m-%d').replace(tzinfo=UTC) <
                                    (datetime.now(UTC) - timedelta(days=180)) and
                    history[-1]['status'] == 'open'):
                        return JSONResponse(status_code=200, content=reject_json)

                # начало скоринга
                score += score_age_repeater(client_data['age'])
                score += score_income(client_data['monthly_income'])
                score += score_employment_type(client_data['employment_type'])

                if client_data['has_property']:
                    score+=2

                score += score_history_first(history)

                score += score_history_summ_last(history)

                match score:
                    case score if score <= 4:
                        logging.info(f'Client {request_body.phone}')
                        return JSONResponse(status_code=200, content=reject_json)
                    case score if 5 <= score <= 6:
                        product_name = 'LoyaltyLoan'
                    case score if 7 <= score <= 8:
                        product_name = 'AdvantagePlus'
                    case _:
                        product_name = 'PrimeCredit'

                product = find_product_by_start_index(request_body.products,
                                                    REPEATER_PRODUCTS,
                                                    start_index=REPEATER_PRODUCTS.index(product_name))

                if product is None:
                    return JSONResponse(status_code=200, content=reject_json)

                current_time = datetime.now(UTC).strftime('%Y%m%d%H%M%S')

                kafka_message = {
                    'version': 1,
                    'occurred_at':
                        datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]+'Z',
                    'phone': request_body.phone,
                    'event': 'repeater_accepted',
                    'profile': None,
                    'history_entry': {
                        'loan_id': f'loan_{request_body.phone}_{current_time}',
                        'product_name': product_name,
                        'amount': product.max_amount,
                        'issue_date': datetime.now(UTC).strftime('%Y-%m-%d'),
                        'term_days': product.term_days,
                        'status': 'open',
                        'close_date': None
                    }
                }
                producer: KafkaProducer = request.app.state.producer

                try:
                    await producer.send(message=kafka_message,
                                        key=request_body.phone)
                except KafkaError as kafka_error:
                    scoring_logger.error(f'Error: {kafka_error}'
                                        f'Phone: {request_body.phone}')
                scoring_logger.info(msg = {'decision': 'accepted',
                                        'product': product.model_dump()})
                return JSONResponse(status_code=200,
                                    content={'decision': 'accepted',
                                            'product': product.model_dump()})

        return JSONResponse(status_code=500, content={'Error': 'Server error'})
