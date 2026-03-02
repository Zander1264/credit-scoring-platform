import logging
from datetime import UTC, datetime, timedelta
from enum import StrEnum

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.api.logic import (
    score_age,
    score_employment_type,
    score_income,
    score_overdue_payments,
    score_profile_edit,
    score_property_low_income,
    score_request_count,
)
from app.api.schemas import PioneerSchema, RepeaterSchema
from app.config import set_config

antifraud_router = APIRouter(prefix='/antifraud', tags=['Антифрод'])

config = set_config('data_service')

class RejectReasons(StrEnum):
    """
    Reject Reasons.
    """
    # Base
    B1 = 'Young age. Must be 18 or older.'
    B2 = 'Monthly income is below minimum threshold (min: 10,000 RUB).'
    B3 = 'Unemployed.'

    # Pioneer
    P1 = 'Daily application limit exceeded (4 applications in 24 hours). Max: 3'
    P2 = 'Low Income Real Estate'

    # Repeater
    R1 = 'Overdue payments.'
    R2 = 'Profile has been heavily modified in last 30 days.'

@antifraud_router.post('/pioneer/check',
                       summary='Проверка Pioneer',
                       description='Антифрод проверка для Pioneer пользователя.')
async def check_pioneer(data: PioneerSchema) -> JSONResponse:
    reject_reasons:list[str] = []
    user_data = data.user_data
    if not score_age(user_data.age):
        reject_reasons.append(RejectReasons.B1)
    if not score_income(user_data.monthly_income):
        reject_reasons.append(RejectReasons.B2)
    if not score_employment_type(user_data.employment_type):
        reject_reasons.append(RejectReasons.B3)
    if not await score_request_count(user_data.phone):
        reject_reasons.append(RejectReasons.P1)
    if not score_property_low_income(user_data.has_property,
                                 user_data.monthly_income):
        reject_reasons.append(RejectReasons.P2)
    if len(reject_reasons) > 0:
        return JSONResponse(status_code=200,
                            content={
                                'decision': 'rejected',
                                'reasons': reject_reasons
                            })
    return JSONResponse(status_code=200,
                        content={
                            'decision': 'passed',
                            'reasons': []
                        })

@antifraud_router.post('/repeater/check',
                       summary='Проверка Repeater',
                       description='Антифрод проверка для Repeater пользователя.')
async def check_repeater(request: RepeaterSchema) -> JSONResponse:
    base_url = config['base_url']
    reject_reasons:list[str] = []
    phone = request.phone
    current_profile = request.current_profile
    try:
        async with httpx.AsyncClient(base_url=base_url,
                            timeout=config['timeout']) as async_client:
            loans_history_response = await async_client.get(
                f'/loans-data?phone={phone}')
        loans_history = loans_history_response.json() # returns list of dicts
    except HTTPException as e:
        logging.error(f'Error connecting to data service: {e}')
        raise HTTPException(status_code=502,
                            detail='Error connecting to data service') from e
    except Exception as e:
        logging.error(f'Unexpected error: {e}')
        raise HTTPException(status_code=500,
                            detail='Unexpected server error') from e

    last_loan = loans_history[-1]
    date_of_last_loan = last_loan['issue_date']
    previous_profile = last_loan['profile_snapshot']
    if not score_age(current_profile.age):
        reject_reasons.append(RejectReasons.B1)
    if not score_income(current_profile.monthly_income):
        reject_reasons.append(RejectReasons.B2)
    if not score_employment_type(current_profile.employment_type):
        reject_reasons.append(RejectReasons.B3)
    if not await score_overdue_payments(loans_history):
        reject_reasons.append(RejectReasons.R1)

    if ((datetime.now(UTC) -
            datetime.fromisoformat(date_of_last_loan).astimezone(UTC)
            < timedelta(days=30)) and
        not await score_profile_edit(current_profile.model_dump(),
                                        previous_profile)):
        reject_reasons.append(RejectReasons.R2)
    if len(reject_reasons) > 0:
        return JSONResponse(status_code=200,
                            content={
                                'decision': 'rejected',
                                'reasons': reject_reasons
                            })
    return JSONResponse(status_code=200,
                        content={
                            'decision': 'passed',
                            'reasons': []
                        })

