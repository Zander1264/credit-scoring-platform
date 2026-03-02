from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class ProfileSchema(BaseModel):
    age: int = Field(description='Возраст клиента', ge=1, le=120)
    monthly_income: int = Field(description='Доход клиента в рублях', ge=0)
    employment_type: Literal['full_time',
                             'freelance'] = Field(description='Формат работы')
    has_property: bool = Field(description='Наличие недвижимости')

class LoanEntryNewSchema(BaseModel):
    loan_id: str = Field(description='Идентификатор кредита')
    product_name: str = Field(description='Название продукта')
    amount: int = Field(description='Сумма кредита', ge=1)
    issue_date: str = Field(description='Дата выдачи кредита',
                            pattern=r'^(\d{4})-(\d{2})-(\d{2})$')
    term_days: int = Field(description='Срок кредита в днях', ge=1)
    status: Literal['open',
                  'closed',] = Field(description='Статус кредита')
    close_date: str|None = Field(description='Дата закрытия кредита',
                                 pattern=r'^(\d{4})-(\d{2})-(\d{2})$')

    @field_validator('issue_date', mode='after')
    @classmethod
    def validate_issue_date(cls, value: str) -> str:
        try:
            datetime.strptime(value, '%Y-%m-%d').astimezone(UTC)
            return value
        except ValueError as exc:
            raise RuntimeError(f'Incorrect date format {value}. '
                               f'Should be YYYY-MM-DD.') from exc

    @field_validator('close_date', mode='after')
    @classmethod
    def validate_close_date(cls, value: str|None, info: ValidationInfo) -> str|None:
        status = info.data.get('status')
        if status == 'open':
            if value is None:
                return None
            raise ValueError(f'Incorrect date format {value}. Should be None.')
        if value is None:
            raise ValueError(f'Incorrect date format {value}. Should be YYYY-MM-DD.')
        try:
            datetime.strptime(value, '%Y-%m-%d').astimezone(UTC)
            return value
        except ValueError as exc:
            raise RuntimeError(f'Incorrect date format {value}. '
                               f'Should be YYYY-MM-DD.') from exc

class LoanEntryUpdateSchema(BaseModel):
    loan_id: str = Field(description='Идентификатор кредита')
    status: Literal['closed'] = Field(description='Статус кредита')
    close_date: str = Field(description='Дата закрытия кредита',
                            pattern=r'^(\d{4})-(\d{2})-(\d{2})$')

    @field_validator('close_date', mode='after')
    @classmethod
    def validate_issue_date(cls, value: str) -> str:
        if value is None:
            raise ValueError(f'Incorrect date format {value}. Should be YYYY-MM-DD.')
        try:
            datetime.strptime(value, '%Y-%m-%d').astimezone(UTC)
            return value
        except ValueError as exc:
            raise RuntimeError(f'Incorrect date format {value}. '
                               f'Should be YYYY-MM-DD.') from exc

class ProfileRequestSchema(BaseModel):
    phone: str = Field(description='Телефон клиента', pattern=r'^\b7\d{10}$')
    profile: ProfileSchema = Field(description='Профиль клиента')

class LoanEntryRequestSchema(BaseModel):
    phone: str = Field(description='Телефон клиента', pattern=r'^\b7\d{10}$')
    loan_entry: (LoanEntryNewSchema |
                 LoanEntryUpdateSchema) = Field(description='Запись кредита')

class CombinedRequestSchema(BaseModel):
    phone: str = Field(description='Телефон клиента', pattern=r'^\b7\d{10}$')
    profile: ProfileSchema = Field(description='Профиль клиента')
    loan_entry: (LoanEntryNewSchema |
                 LoanEntryUpdateSchema) = Field(description='Запись кредита')
