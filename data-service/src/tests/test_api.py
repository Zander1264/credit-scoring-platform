import asyncio
from logging import DEBUG, FileHandler, basicConfig, getLogger
import os
from dotenv import load_dotenv
from sqlalchemy import URL, select, text
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import pytest
import pytest_asyncio
from datetime import datetime
from app.db.database import get_session
from app.db.models import Base, Loans, Users
from app.service import create_app

logger = getLogger(__name__)
FORMAT = "%(asctime)s : %(name)s : %(levelname)s : %(funcName)s : %(lineno)d : %(message)s"
basicConfig(level=DEBUG, format=FORMAT, handlers=[
    FileHandler("src/tests/tests.log")],
            force=True)

load_dotenv()
#SQLALCHEMY_DATABASE_URL = "postgresql+asyncpg://test_user:test_password@db:5433/test_database"


SQLALCHEMY_DATABASE_URL = str(os.environ.get('DATABASE_URL'))

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=True,
    poolclass=NullPool,
)

# async def check_connection() -> None:
#     database_url = URL.create(
#         drivername='postgresql+asyncpg',
#         username='test_user',
#         password='test_password',
#         host='db',
#         port=5433,
#         database='test_database'
#     )
#     engine = create_async_engine(database_url)
#     try:
#         async with engine.connect() as conn:
#             result = await conn.execute(text('SELECT 1'))
#             logger.info(result.fetchone())
#     except Exception as e:
#         logger.error(f"Database connection failed: {e}")
#         raise

# check_connection()

TestingLocalSession = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False
)

async def init_test_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

async def override_get_session():
    db = TestingLocalSession()
    try:
        yield db
    finally:
        await db.close()


@pytest.fixture()
def client():
    app = create_app()
    app.dependency_overrides[get_session] = override_get_session
    yield TestClient(app)



@pytest_asyncio.fixture(scope='module', autouse=True)
async def create_test_db():
    await init_test_db()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope='module')
def users_list():
    return [
        {
            'phone': '78945614521',
            'age': 25,
            'monthly_income': 55000,
            'employment_type': 'full_time',
            'has_property': True
        },
        {
            'phone': '78945612345',
            'age': 30,
            'monthly_income': 60000,
            'employment_type': 'part_time',
            'has_property': False
        },
        {
            'phone': '78945412347',
            'age': 50,
            'monthly_income': 70000,
            'employment_type': 'full_time',
            'has_property': True
        }
    ]

@pytest.fixture(scope='module')
def loans_list():
    return [
        {
            'loan_id': 'loan_20250101_001',
            'product_name': 'LoyaltyLoan',
            'amount': 60000,
            'issue_date': datetime.strptime('2025-01-01', '%Y-%m-%d'),
            'term_days': 120,
            'status': 'closed',
            'close_date': datetime.strptime('2025-04-01', '%Y-%m-%d'),
            'profile_id': 1,
            'profile_snapshot': {
            'phone': '78945614521',
            'age': 25,
            'monthly_income': 55000,
            'employment_type': 'full_time',
            'has_property': True
            }
        },
        {
            'loan_id': 'loan_20250101_002',
            'product_name': 'PrimeCredit',
            'amount': 100000,
            'issue_date': datetime.strptime('2025-01-01', '%Y-%m-%d'),
            'term_days': 180,
            'status': 'open',
            'close_date': None,
            'profile_id': 1,
            'profile_snapshot': {
            'phone': '78945614521',
            'age': 25,
            'monthly_income': 55000,
            'employment_type': 'full_time',
            'has_property': True
            }
        },
        {
            'loan_id': 'loan_20250101_003',
            'product_name': 'PrimeCredit',
            'amount': 150000,
            'issue_date': datetime.strptime('2025-01-01', '%Y-%m-%d'),
            'term_days': 180,
            'status': 'closed',
            'close_date': datetime.strptime('2025-07-01', '%Y-%m-%d'),
            'profile_id': 2,
            'profile_snapshot': {
            'phone': '78945612345',
            'age': 30,
            'monthly_income': 60000,
            'employment_type': 'part_time',
            'has_property': False
        }
        },
        {
            'loan_id': 'loan_20250101_004',
            'product_name': 'LoyaltyLoan',
            'amount': 80000,
            'issue_date': datetime.strptime('2025-01-01', '%Y-%m-%d'),
            'term_days': 120,
            'status': 'closed',
            'close_date': datetime.strptime('2025-04-01', '%Y-%m-%d'),
            'profile_id': 2,
            'profile_snapshot': {
            'phone': '78945612345',
            'age': 30,
            'monthly_income': 60000,
            'employment_type': 'part_time',
            'has_property': False
        }
        },
        {
            'loan_id': 'loan_20250101_005',
            'product_name': 'PrimeCredit',
            'amount': 120000,
            'issue_date': datetime.strptime('2025-01-01', '%Y-%m-%d'),
            'term_days': 180,
            'status': 'open',
            'close_date': None,
            'profile_id': 3,
            'profile_snapshot': {
            'phone': '78945412347',
            'age': 50,
            'monthly_income': 70000,
            'employment_type': 'full_time',
            'has_property': True
        }
        },
        {
            'loan_id': 'loan_20250101_006',
            'product_name': 'LoyaltyLoan',
            'amount': 70000,
            'issue_date': datetime.strptime('2025-01-01', '%Y-%m-%d'),
            'term_days': 120,
            'status': 'open',
            'close_date': None,
            'profile_id': 3,
            'profile_snapshot': {
            'phone': '78945412347',
            'age': 50,
            'monthly_income': 70000,
            'employment_type': 'full_time',
            'has_property': True
        }
        }
    ]

async def insert_test_data(users_list, loans_list, session: AsyncSession):
    users_to_add = []
    for user_data in users_list:
        user = Users(**user_data)
        users_to_add.append(user)
    session.add_all(users_to_add)
    await session.flush()

    all_users = await session.scalars(select(Users))
    users_map = {user.phone: user for user in all_users}

    loans_to_add = []
    for loan_data in loans_list:
        first_user = next(iter(users_map.values()))
        loan = Loans(#profile_id=first_user.id,
                     **loan_data)
        loans_to_add.append(loan)
    session.add_all(loans_to_add)
    await session.commit()

@pytest_asyncio.fixture(scope='module', autouse=True)
async def prepare_test_database(users_list, loans_list):
    async with TestingLocalSession() as session:
        await insert_test_data(users_list, loans_list, session)

@pytest.fixture
def request_data_combined_correct():
    return {
        "phone": "78945614521",
        "profile": {
            "age": 25,
            "monthly_income": 55000,
            "employment_type": "full_time",
            "has_property": True
        },
        "loan_entry": {
            "loan_id": "loan_20250101_100",
            "product_name": "PrimeCredit",
            "amount": 150000,
            "issue_date": "2025-09-15",
            "term_days": 180,
            "status": "open",
            "close_date": None
        }
    }

@pytest.fixture
def request_data_combined_correct_loan_exists():
    return {
        "phone": "78945614521",
        "profile": {
            "age": 25,
            "monthly_income": 55000,
            "employment_type": "full_time",
            "has_property": True
        },
        "loan_entry": {
            "loan_id": "loan_20250101_001",
            "product_name": "PrimeCredit",
            "amount": 150000,
            "issue_date": "2025-09-15",
            "term_days": 180,
            "status": "open",
            "close_date": None
        }
    }

@pytest.fixture
def request_data_combined_not_found():
    return {
        "phone": "78945123345",
        "profile": {
            "age": 25,
            "monthly_income": 55000,
            "employment_type": "full_time",
            "has_property": True
        },
        "loan_entry": {
            "loan_id": "loan_20250101_080",
            "product_name": "PrimeCredit",
            "amount": 150000,
            "issue_date": "2025-09-15",
            "term_days": 180,
            "status": "open",
            "close_date": None
        }
    }

@pytest.fixture
def request_data_profile_edit():
    return {
        "phone": "78945614521",
        "profile": {
            "age": 30,
            "monthly_income": 60000,
            "employment_type": "full_time",
            "has_property": False
        }
    }

@pytest.fixture
def request_data_profile_new():
    return {
        "phone": "78945412348",
        "profile": {
            "age": 50,
            "monthly_income": 70000,
            "employment_type": "full_time",
            "has_property": True
        }
    }

@pytest.fixture
def request_data_loan_entry_new():
    return {
        "phone": "78945614521",
        "loan_entry": {
            "loan_id": "loan_20250101_200",
            "product_name": "PrimeCredit",
            "amount": 150000,
            "issue_date": "2025-09-15",
            "term_days": 180,
            "status": "open",
            "close_date": None
        }
    }

@pytest.fixture
def request_data_loan_entry_exists():
    return {
        "phone": "78945614521",
        "loan_entry": {
            "loan_id": "loan_20250101_001",
            "product_name": "PrimeCredit",
            "amount": 150000,
            "issue_date": "2025-09-15",
            "term_days": 180,
            "status": "open",
            "close_date": None
        }
    }

@pytest.fixture
def request_data_loan_entry_edit():
    return {
        "phone": "78945614521",
        "loan_entry": {
            "loan_id": "loan_20250101_001",
            "status": "closed",
            "close_date": "2025-09-15"
        }
    }

def test_get_user_data(client):
    query = '78945614521'
    response = client.get(f'/user-data?phone={query}')
    assert response.status_code == 200

    query = '78945614522123'
    response = client.get(f'/user-data?phone={query}')
    assert response.status_code == 422

    query = '78945614522'
    response = client.get(f'/user-data?phone={query}')
    assert response.status_code == 404

def test_update_user_data_new_profile(request_data_profile_new, client):
    response = client.put('/user-data',
                          json=request_data_profile_new)
    assert response.status_code == 201


def test_update_user_data_edit_profile(request_data_profile_edit, client):
    response = client.put('/user-data',
                          json=request_data_profile_edit)
    assert response.status_code == 200

    
def test_update_user_data_new_loan_entry(request_data_loan_entry_new, client):
    response = client.put('/user-data',
                          json=request_data_loan_entry_new)
    assert response.status_code == 200

def test_update_user_data_new_loan_entry_exists(request_data_loan_entry_exists, client):
    response = client.put('/user-data',
                          json = request_data_loan_entry_exists)
    assert response.status_code == 409

def test_update_user_data_edit_loan_entry(request_data_loan_entry_edit, client):
    response = client.put('/user-data',
                          json = request_data_loan_entry_edit)
    assert response.status_code == 200

def test_update_user_data_combined(request_data_combined_correct,
                                   request_data_combined_not_found,
                                   request_data_combined_correct_loan_exists,
                                   client):
    response = client.put('/user-data',
                          json = request_data_combined_correct)
    assert response.status_code == 200

    response = client.put('/user-data',
                          json = request_data_combined_not_found)
    assert response.status_code == 201

    response = client.put('/user-data',
                          json = request_data_combined_correct_loan_exists)
    assert response.status_code == 409