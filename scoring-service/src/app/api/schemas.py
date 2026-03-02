from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class PioneerProductName(str, Enum):
    MICRO_LOAN = 'MicroLoan',
    QUICK_MONEY = 'QuickMoney',
    CONSUMER_LOAN = 'ConsumerLoan'

class RepeaterProductName(str, Enum):
    LOYALTY_LOAN = 'LoyaltyLoan'
    ADVANTAGE_PLUS = 'AdvantagePlus'
    PRIME_CREDIT = 'PrimeCredit'

class PioneerDataSchema(BaseModel):
    phone: str = Field(description='Телефон клиента', pattern=r'^\b7\d{10}$')
    age: int = Field(description='Возраст клиента', ge=1, le=150)
    monthly_income: int = Field(description='Доход клиента в рублях', ge=0)
    employment_type: str = Field(description='Формат работы')
    has_property: bool = Field(description='Наличие недвижимости')

class PioneerProductSchema(BaseModel):
    name: Literal['MicroLoan',
                  'QuickMoney',
                  'ConsumerLoan'] = Field(description='Название продукта')
    max_amount: int = Field(description='Максимальная сумма кредита')
    term_days: int = Field(description='Срок кредита в днях', ge=1)
    interest_rate_daily: float = Field(description='Процентная ставка в день',
                                       ge=0.01,
                                       le=100)


class RepeaterProductSchema(BaseModel):
    name: RepeaterProductName = Field(description='Название продукта')
    max_amount: int = Field(description='Максимальная сумма кредита')
    term_days: int = Field(description='Срок кредита в днях', ge=1)
    interest_rate_daily: float = Field(description='Процентная ставка в день',
                                       ge=0.01,
                                       le=100)

class RepeaterRequestSchema(BaseModel):
    phone: str = Field(description='Телефон клиента', pattern=r'^\b7\d{10}$',)
    products: list[RepeaterProductSchema] = Field(description='Список продуктов')
