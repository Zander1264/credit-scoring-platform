import json
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, TIMESTAMP, ForeignKey, literal_column
from sqlalchemy.event import listen
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass

class Users(Base):
    """Таблица Пользователей"""

    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True,autoincrement=True)
    phone: Mapped[str]
    age: Mapped[int]
    monthly_income: Mapped[int]
    employment_type: Mapped[str]
    has_property: Mapped[bool]

class Loans(Base):
    """Таблица Кредитов"""

    __tablename__ = 'loans'
    id: Mapped[int] = mapped_column(primary_key=True,autoincrement=True)
    loan_id: Mapped[str] = mapped_column(unique=True)
    product_name: Mapped[str]
    amount: Mapped[int]
    issue_date: Mapped[str] = mapped_column(TIMESTAMP(timezone=True))
    term_days: Mapped[int]
    status: Mapped[str]
    close_date: Mapped[str] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    profile_snapshot: Mapped[Any] = mapped_column(JSON)

    users: Mapped['Users'] = relationship()

class Products(Base):
    """Таблица Продуктов"""

    __tablename__ = 'products'
    id: Mapped[int] = mapped_column(primary_key=True,autoincrement=True)
    name: Mapped[str]
    flow_type: Mapped[str]

class UserSnapshot(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    phone: str
    age: int
    monthly_income: int
    employment_type: str
    has_property: bool

def generate_profile_snapshot(_: object, __: object, target: Loans) -> None:
    user = target.users
    if user:
        serialized_snapshot = UserSnapshot.model_validate(user).model_dump(mode='json')
        json_string = json.dumps(serialized_snapshot)
        target.profile_snapshot = literal_column(f"'{json_string}'").cast(JSON)

listen(Loans, 'before_insert', generate_profile_snapshot)
