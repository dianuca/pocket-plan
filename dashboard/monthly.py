from decimal import Decimal
from django.db.models import Sum
from finances.models import Expense, Income, Installment
from finances.savings import savings_evolution, savings_summary
from finances.personal_budget import personal_budget_summary
from .services import calculate_expenses
from finances.periods import budget_period, installment_for_period, period_context


def monthly_context(owner, selected_month):
    start, end = budget_period(owner, selected_month)
    income = Income.objects.filter(
        owner=owner,
        received_on__range=(start, end),
    ).aggregate(total=Sum("amount"))["total"]
    if income is None:
        income = Decimal("0.00")
    monthly_expenses = Expense.objects.filter(
        owner=owner,
        paid_on__range=(start, end),
    )
    expense_items = list(
        monthly_expenses
        .order_by("-paid_on", "-pk")
        .values("name", "amount")
    )
    category_labels = dict(Expense.Category.choices)
    expenses_by_category = [
        {
            "category": row["category"],
            "label": category_labels[row["category"]],
            "amount": row["total"],
        }
        for row in monthly_expenses.values("category")
        .annotate(total=Sum("amount"))
        .order_by("category")
    ]
    installment_items = []
    installment_total = Decimal("0.00")

    installments = Installment.objects.filter(
        owner=owner,
    ).order_by("name", "pk")

    for installment in installments:
        amount, remaining = installment_for_period(installment, start, end)
        if not amount:
            continue

        installment_items.append({
            "name": installment.name,
            "amount": amount,
            "remaining": remaining,
        })
        installment_total += amount

    if installment_total > Decimal("0.00"):
        expenses_by_category.append({
            "category": "installments",
            "label": "Rate",
            "amount": installment_total,
        })

    expenses = calculate_expenses(expense_items) + installment_total
    savings = savings_summary(owner, selected_month)
    balance = income - expenses - savings["savings_deposits"] + savings["savings_withdrawals"]

    personal = personal_budget_summary(owner, selected_month)

    context = {
        "income": income,
        "expenses": expenses,
        "balance": balance,
        "unallocated_balance": balance - personal["personal_reserved"],
        "direct_expenses": expenses - installment_total,
        **personal,
        "savings_evolution": savings_evolution(owner, selected_month),
        **savings,
        "selected_month": selected_month,
        **period_context(owner, selected_month),
        "expense_items": expense_items,
        "installment_items": installment_items,
        "installment_total": installment_total,
        "expenses_by_category": expenses_by_category,
        "comparison_max": max(income, expenses),
    }
    return context
