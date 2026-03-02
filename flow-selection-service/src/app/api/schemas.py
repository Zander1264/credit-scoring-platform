from pydantic import BaseModel, Field


class ClientSchema(BaseModel):
    phone: str = Field(description='Телефон клиента', pattern=r'^\b7\d{10}$')
