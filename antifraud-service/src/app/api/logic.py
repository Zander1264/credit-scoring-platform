from enum import StrEnum
from typing import Any

from fastapi import HTTPException

from app.redis_interact import (
    check_redis_connection,
    get_cache,
    redis_client,
    set_cache,
)


def score_age(age: int) -> bool:
    return age >= 18

def score_income(income: int) -> bool:
    return income >= 10000

def score_employment_type(employment_type: str) -> bool:
    return employment_type != 'unemployed'

def score_property_low_income(property: bool, income: int) -> bool:
    if property:
        return income >= 30000
    return True

async def score_request_count(phone: str) -> bool:
    if check_redis_connection(redis_client):
        redis_data = await get_cache(redis_client, phone)
        if not redis_data['cache']:
            await set_cache(redis_client, phone, 1)
            return True
        if int(redis_data['value']) < 3:
            await set_cache(r=redis_client,
                      name=phone,
                      value=int(redis_data['value'])+1,
                      ttl=redis_data['ttl'])
            return True
        return False
    raise HTTPException(status_code=502, detail='Redis unavailable')

async def score_overdue_payments(loans_history: list[dict[str, Any]]) -> bool:
    return all(loan['status'] != 'overdue' for loan in loans_history)

class EmploymentType(StrEnum):
    FULL_TIME = 'full-time'
    FREELANCE = 'freelance'
    UNEMPLOYED = 'unemployed'

async def score_profile_edit(current_profile: dict[str, Any],
                             previous_profile: dict[str, Any]) -> bool:
    downgrade_types = (EmploymentType.FREELANCE, EmploymentType.UNEMPLOYED)
    if ((current_profile['monthly_income'] >= 2 * previous_profile['monthly_income']) or
        (current_profile['monthly_income'] <= previous_profile['monthly_income'] / 2)):
        result = False
    else:
        result = not (previous_profile['employment_type'] == EmploymentType.FULL_TIME
                    and current_profile['employment_type'] in downgrade_types)
    return result

