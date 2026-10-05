from decimal import Decimal


def calculate_expenses(items):
    return sum(
        (item["amount"] for item in items),
        Decimal("0.00"),
    )