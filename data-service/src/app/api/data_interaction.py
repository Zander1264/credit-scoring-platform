import logging
import re
import traceback
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import join, select, update

from app.api.schemas import (
    CombinedRequestSchema,
    LoanEntryNewSchema,
    LoanEntryRequestSchema,
    LoanEntryUpdateSchema,
    ProfileRequestSchema,
)
from app.db.dependencies import SessionDep
from app.db.models import Loans, Products, Users
from app.monitoring.tracing import get_tracer

data_router = APIRouter()

tracer = get_tracer()

async def get_loans_history(phone: str, session: SessionDep) -> Any:
    query_loans = (select(Loans).join_from(Loans, Users)
                                .where(Users.phone == phone))
    result = await session.execute(query_loans)
    return result.mappings().all()

@data_router.get('/user-data', summary='Получить данные пользователя')
async def get_user_data(phone: str, session: SessionDep) -> JSONResponse:
    if not re.match(r'^\b7\d{10}$', phone):
        raise HTTPException(status_code=422, detail='Invalid phone number')

    with tracer.start_as_current_span('get_user_data'):
        try:
            query = (select(Users.phone.label('phone'), Users.age, Users.monthly_income,
                            Users.employment_type, Users.has_property,
                            Loans.loan_id, Loans.product_name, Loans.amount,
                            Loans.issue_date, Loans.term_days, Loans.status,
                            Loans.close_date)
                    .select_from(join(Users, Loans, Users.id == Loans.profile_id))
                    .where(Users.phone == phone)
                    .order_by(Loans.issue_date.desc()))
            result = await session.execute(query)
            rows = result.all()
            if not rows:
                logging.info(f'User with phone {phone} not found')
                raise HTTPException(status_code=404, detail='User not found')

            user_data = {
                'phone': rows[0].phone,
                'profile': {
                    'age': rows[0].age,
                    'monthly_income': rows[0].monthly_income,
                    'employment_type': rows[0].employment_type,
                    'has_property': rows[0].has_property
                },
                'history': [
                    {
                        'loan_id': row.loan_id,
                        'product_name': row.product_name,
                        'amount': row.amount,
                        'issue_date': row.issue_date.isoformat(),
                        'term_days': row.term_days,
                        'status': row.status,
                        'close_date': row.close_date.isoformat() if
                            row.close_date else None
                    }
                    for row in rows
                ]
            }

            return JSONResponse(content=user_data, status_code=200)


        except HTTPException:
            raise
        except Exception as e:
            logging.error(f'Error getting user data for user {phone}: {e}')
            logging.debug(traceback.format_exc())
            raise RuntimeError(f'Internal server error: {e}') from e



@data_router.put('/user-data', summary='Обновить данные пользователя')
async def update_user_data(request: (CombinedRequestSchema |
                               ProfileRequestSchema |
                               LoanEntryRequestSchema),
                     session: SessionDep) -> JSONResponse:
    phone = request.phone
    client_exists = False
    with tracer.start_as_current_span('update_user_data'):

        if isinstance(request, CombinedRequestSchema):
            try:
                query_profile = (select(Users.phone, Users.age, Users.monthly_income,
                                Users.employment_type, Users.has_property)
                        .where(Users.phone == phone))
                result = await session.scalar(query_profile)
                profile = request.profile
                if result:
                    # Обновляем в базе данные пользователя
                    client_exists = True
                    updated_profile_query = (update(Users)
                                    .values(age = profile.age,
                                            monthly_income = profile.monthly_income,
                                            employment_type = profile.employment_type,
                                            has_property = profile.has_property)
                                    .where(Users.phone == phone))
                    await session.execute(updated_profile_query)
                    await session.flush()
                    logging.info(f'User profile updated for phone {phone}')

                else:
                    # Добавляем в базу нового пользователя
                    client_exists = False
                    session.add(Users(phone = phone,
                                    **profile.model_dump()))
                    await session.flush()
                    logging.info(f'New user added with phone {phone}')

            except Exception as e:
                await session.rollback()
                logging.error(f'Error creating/updating user profile'
                            f'for phone {phone}: {e}')
                logging.debug(traceback.format_exc())
                raise RuntimeError(f'Internal server error: {e}') from e


            profile_id = await session.execute(select(Users.id)
                                        .where(Users.phone == phone))
            profile_id = profile_id.first()[0]
            user_q = select(Users).where(Users.id == profile_id)
            user = (await session.execute(user_q)).scalar_one_or_none()
            if isinstance(request.loan_entry, LoanEntryNewSchema):
                loan_entry = request.loan_entry
                try:
                    loans_history = await get_loans_history(phone, session)
                    if loans_history:
                        loan_ids = [next(iter(item.values())).loan_id for
                                    item in loans_history]
                        for loan_id in loan_ids:
                            if loan_id == loan_entry.loan_id:
                                raise HTTPException(status_code=409,
                                                    detail='Loan already exists')
                    # добавляем новую запись в историю пользователя
                    new_loan_dict = loan_entry.model_dump()
                    session.add(Loans(loan_id = new_loan_dict['loan_id'],
                                    product_name = new_loan_dict['product_name'],
                                    amount = new_loan_dict['amount'],
                                    issue_date =
                                    datetime.strptime(new_loan_dict['issue_date'],
                                                    '%Y-%m-%d').replace(tzinfo=UTC),
                                    term_days = new_loan_dict['term_days'],
                                    status = new_loan_dict['status'],
                                    close_date = None
                                    if not new_loan_dict['close_date']
                                    else datetime.strptime(new_loan_dict['close_date'],
                                                            '%Y-%m-%d').replace(tzinfo=UTC),
                                    users = user))
                    await session.flush()
                except HTTPException:
                    raise
                except Exception as e:
                    await session.rollback()
                    logging.error(f'Error creating loan for user {phone}: {e}')
                    logging.debug(traceback.format_exc())
                    raise RuntimeError(f'Internal server error: {e}') from e
                else:
                    await session.commit()
                    if client_exists:
                        return JSONResponse(content={
                            'updated_profile':profile.model_dump(),
                            'new_loan':loan_entry.model_dump()},
                            status_code=200)
                    return JSONResponse(content={'new_profile':profile.model_dump(),
                                            'new_loan':loan_entry.model_dump()},
                                            status_code=201)

            if isinstance(request.loan_entry, LoanEntryUpdateSchema):
                loan_entry = request.loan_entry
                try:
                    loans_history = await get_loans_history(phone, session)
                    if not loans_history:
                        raise HTTPException(status_code=404, detail='Loan not found')
                    # Обновляем в базе данные кредита
                    updated_loan_query = (update(Loans)
                                        .values(status = loan_entry.status,
                                                close_date = loan_entry.close_date)
                                        .where(Loans.profile_id == profile_id,
                                                Loans.loan_id == loan_entry.loan_id))
                    session.execute(updated_loan_query)
                    await session.flush()
                except HTTPException:
                    raise
                except Exception as e:
                    await session.rollback()
                    logging.error(f'Error updating loan for user {phone}: {e}')
                    logging.debug(traceback.format_exc())
                    raise RuntimeError(f'Internal server error: {e}') from e
                else:
                    await session.commit()
                    if client_exists:
                        return JSONResponse(content={'new_profile':profile.model_dump(),
                                                'new_loan':loan_entry.model_dump()},
                                                status_code=200)
                    return JSONResponse(content={'new_profile':profile.model_dump(),
                                            'new_loan':loan_entry.model_dump()},
                                            status_code=201)

        if isinstance(request, ProfileRequestSchema):
            try:
                query_profile = (select(Users.phone, Users.age, Users.monthly_income,
                                Users.employment_type, Users.has_property)
                        .where(Users.phone == phone))
                result = await session.scalar(query_profile)
                profile = request.profile
                if result:
                    # Обновляем в базе данные пользователя
                    client_exists = True
                    updated_profile_query = (update(Users)
                                    .values(age = profile.age,
                                            monthly_income = profile.monthly_income,
                                            employment_type = profile.employment_type,
                                            has_property = profile.has_property)
                                    .where(Users.phone == phone))
                    await session.execute(updated_profile_query)
                    await session.flush()
                    logging.info(f'User profile updated for phone {phone}')

                else:
                    # Добавляем в базу нового пользователя
                    client_exists = False
                    session.add(Users(phone = phone,
                                    **profile.model_dump()))
                    await session.flush()
                    logging.info(f'New user added with phone {phone}')

            except Exception as e:
                await session.rollback()
                logging.error(f'Error creating/updating user profile'
                            f'for phone {phone}: {e}')
                logging.debug(traceback.format_exc())
                raise RuntimeError(f'Internal server error: {e}') from e
            else:
                if client_exists:
                    return JSONResponse(content={
                        'updated_profile':profile.model_dump()},
                        status_code=200)
                return JSONResponse(content={
                    'new_profile':profile.model_dump()},
                    status_code=201)

        if isinstance(request, LoanEntryRequestSchema):
            profile_id = await session.execute(select(Users.id)
                                        .where(Users.phone == phone))
            profile_id = profile_id.first()[0]
            user_q = select(Users).where(Users.id == profile_id)
            user = (await session.execute(user_q)).scalar_one_or_none()
            if not profile_id:
                logging.error(f'User not found for phone {phone}')
                raise HTTPException(status_code=404, detail='User not found')

            if isinstance(request.loan_entry, LoanEntryNewSchema):
                loan_entry = request.loan_entry
                try:
                    loans_history = await get_loans_history(phone, session)
                    if loans_history:
                        loan_ids = [next(iter(item.values())).loan_id
                                    for item in loans_history]
                        for loan_id in loan_ids:
                            if loan_id == loan_entry.loan_id:
                                raise HTTPException(status_code=409,
                                                    detail='Loan already exists')
                    # добавляем новую запись в историю пользователя
                    new_loan_dict = loan_entry.model_dump()
                    session.add(Loans(loan_id = new_loan_dict['loan_id'],
                                    product_name = new_loan_dict['product_name'],
                                    amount = new_loan_dict['amount'],
                                    issue_date = datetime.strptime(
                                        new_loan_dict['issue_date'],
                                        '%Y-%m-%d').replace(tzinfo=UTC),
                                    term_days = new_loan_dict['term_days'],
                                    status = new_loan_dict['status'],
                                    close_date = None
                                    if not new_loan_dict['close_date']
                                    else (datetime.strptime(new_loan_dict['close_date'],
                                        '%Y-%m-%d').replace(tzinfo=UTC)),
                                    users = user))
                    await session.flush()
                except HTTPException:
                    raise
                except Exception as e:
                    await session.rollback()
                    logging.error(f'Error creating loan for user {phone}: {e}')
                    logging.debug(traceback.format_exc())
                    raise RuntimeError(f'Internal server error: {e}') from e
                else:
                    await session.commit()
                    return JSONResponse(content={'new_loan':loan_entry.model_dump()},
                                            status_code=200)

            if isinstance(request.loan_entry, LoanEntryUpdateSchema):
                loan_entry = request.loan_entry
                try:
                    query_loans = (select(Loans)
                                .join_from(Loans, Users)
                                .where(Users.phone == phone))
                    result = await session.execute(query_loans)
                    loans_history = result.mappings().all()
                    if not loans_history:
                        raise HTTPException(status_code=404, detail='Loan not found')
                    # Обновляем в базе данные кредита
                    updated_loan_query = (update(Loans)
                                        .values(status = loan_entry.status,
                                                close_date = datetime.strptime(
                                                    loan_entry.close_date,
                                                '%Y-%m-%d').replace(tzinfo=UTC))
                                        .where(Loans.profile_id == profile_id,
                                                Loans.loan_id == loan_entry.loan_id))
                    await session.execute(updated_loan_query)
                    await session.flush()
                except HTTPException:
                    raise
                except Exception as e:
                    await session.rollback()
                    logging.error(f'Error updating loan for user {phone}: {e}')
                    logging.debug(traceback.format_exc())
                    raise RuntimeError(f'Internal server error: {e}') from e
                else:
                    await session.commit()
                    return JSONResponse(content={'new_loan':loan_entry.model_dump()},
                                            status_code=200)

    return JSONResponse(content={'error': 'Invalid request'}, status_code=400)

@data_router.get('/api/products', summary='Получить список продуктов')
async def get_products(flow_type: str, session: SessionDep) -> Any:
    with tracer.start_as_current_span('get_products'):
        try:
            query = select(Products.name).filter(Products.flow_type == flow_type)
            result = await session.execute(query)
            return result.scalars().all()
        except Exception as err:
            logging.error(f'Error getting products for flow type {flow_type}: {err!s}')
            logging.debug(traceback.format_exc())
            raise RuntimeError(f'Internal server error: {err!s}') from err

@data_router.get('/loans-data', summary='Получить историю кредитов пользователя')
async def get_user_loans(phone: str, session: SessionDep) -> JSONResponse:
    try:
        loans_history = await get_loans_history(phone, session)
        if len(loans_history) == 0:
            raise HTTPException(status_code=404, detail='Loans not found')
        loans_as_dicts = [{col.name: val for col,
                        val in loan.items()} for loan in loans_history]
        return JSONResponse(status_code=200, content=loans_as_dicts)
    except HTTPException as e:
        logging.error(f'Error getting loans for user {phone}: {e!s}')
        raise
    except Exception as e:
        logging.error(f'Unknown error getting loans for user {phone}: {e!s}')
        raise
