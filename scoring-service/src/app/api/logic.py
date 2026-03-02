from datetime import UTC, datetime, timedelta

from app.api.schemas import PioneerProductSchema


def score_age_pioneer(age: int) -> int:
    if 18 <= age <= 25:
        return 1
    if 26 <= age <= 40:
        return 3
    return 2

def score_income(income: int) -> int:
    if 10000 <= income <= 29999:
        return 1
    if 30000 <= income <= 49999:
        return 2
    return 3

def score_employment_type(employment_type: str) -> int:
    if employment_type == 'full_time':
        return 3
    if employment_type == 'freelance':
        return 1
    return 0

def find_product_by_start_index(products: list[PioneerProductSchema],
                                products_names: list[str],
                                start_index:int =0) -> PioneerProductSchema | None:
    values_to_check = products_names[start_index:]
    for product_name in values_to_check:
        result = next((i for i in products if i.name == product_name), None)
        if result is not None:
            return result
    return result

def score_age_repeater(age: int) -> int:
    if 21 <= age <= 25:
        return 1
    if 26 <= age <= 40:
        return 3
    return 2

def score_history_first(history: list[dict[str, str]]) -> int:
    issue_date_utc = datetime.strptime(history[0]['issue_date'],
                                       '%Y-%m-%d').replace(tzinfo=UTC)
    if (issue_date_utc < (datetime.now(UTC) - timedelta(days=365)) and
           history[0]['status'] == 'closed'):
            return 3
    return 0

def score_history_summ_last(history: list[dict[str, int]]) -> int:
    if history[-1]['amount'] < 50000:
        return 1
    if history[-1]['amount'] <= 100000:
        return 2
    return 3

def add_product_to_history(product: PioneerProductSchema) -> dict[str, str|int|None]:
    product_name = product.name.value
    product_amount = product.max_amount
    product_issue_date = datetime.now(UTC).strftime('%Y-%m-%d')
    product_term_days = product.term_days
    product_status = 'open'
    product_close_date = None
    return {
        'product_name': product_name,
        'amount': product_amount,
        'issue_date': product_issue_date,
        'term_days': product_term_days,
        'status': product_status,
        'close_date': product_close_date
    }
