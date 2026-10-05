from decimal import Decimal


def calculate_expenses(items):
    return sum(
        (item["amount"] for item in items),
        Decimal("0.00"),
    )

def installment_amount_for_month(
    monthly_amount,
    first_month,
    number_of_installments,
    selected_month,
):
    first_year, first_month_number = map(int, first_month.split("-"))
    selected_year, selected_month_number = map(
        int, selected_month.split("-")
    )

    months_passed = (
        (selected_year - first_year) * 12
        + selected_month_number
        - first_month_number
    )
    if 0 <= months_passed < number_of_installments:
        return monthly_amount
    return Decimal("0.00")

def remaining_installments(
    first_month,
    number_of_installments,
    selected_month,
):
    first_year, first_month_number = map(int, first_month.split("-"))
    selected_year, selected_month_number = map(
        int, selected_month.split("-")
    )
    months_passed = (
        (selected_year - first_year) * 12
        + selected_month_number
        - first_month_number
    )
    elapsed_payment_months = max(months_passed, 0)
    return max(number_of_installments - elapsed_payment_months,0,)