from pydantic import BaseModel, Field


class BaseProfileSchema(BaseModel):
    age: int = Field(description='Возраст клиента', ge=1, le=150)
    monthly_income: int = Field(description='Доход клиента в рублях', ge=0)
    employment_type: str = Field(description='Формат работы')
    has_property: bool = Field(description='Наличие недвижимости')

class PioneerProfileSchema(BaseProfileSchema):
    phone: str = Field(description='Телефон клиента', pattern=r'^\b7\d{10}$')

class PioneerSchema(BaseModel):
    user_data: PioneerProfileSchema = Field(description=
                                            'Профиль нового пользователя')


class RepeaterSchema(BaseModel):
    phone: str = Field(description='Телефон клиента', pattern=r'^\b7\d{10}$')
    current_profile: BaseProfileSchema = Field(description=
                                                   'Текущий профиль польхователя')
