"""Intervale inclusive pentru lunile de buget, etichetate după luna începerii."""
from calendar import monthrange
from datetime import date, timedelta

from django.utils import timezone

from .models import BudgetPreference


def start_day_for(owner):
    return BudgetPreference.objects.filter(owner=owner).values_list("start_day", flat=True).first() or 1


def month_key(value):
    return f"{value.year:04d}-{value.month:02d}"


def month_date(index, day=1):
    year, month = divmod(index, 12)
    return date(year + 1, month + 1, min(day, monthrange(year + 1, month + 1)[1]))


def month_index(value):
    return (value.year - 1) * 12 + value.month - 1


def period_bounds(selected_month, start_day=1):
    index = month_index(date.fromisoformat(f"{selected_month}-01"))
    start = month_date(index, start_day)
    end = month_date(index + 1, start_day) - timedelta(days=1) if index < 119987 else date.max
    return start, end


def budget_period(owner, selected_month):
    return period_bounds(selected_month, start_day_for(owner))


def period_month(owner, value=None):
    value = value or timezone.localdate()
    index = month_index(value)
    if value < month_date(index, start_day_for(owner)):
        index = max(0, index - 1)
    return month_key(month_date(index))


def period_context(owner, selected_month):
    start, end = budget_period(owner, selected_month)
    return {"period_start": start, "period_end": end}


def installment_for_period(installment, start, end):
    first_index = month_index(installment.first_due_on)
    due = []
    for index in range(month_index(start), month_index(end) + 1):
        offset = index - first_index
        if 0 <= offset < installment.number_of_installments:
            scheduled = month_date(index, installment.first_due_on.day)
            if start <= scheduled <= end:
                due.append(offset)
    if due:
        return installment.monthly_amount * len(due), installment.number_of_installments - due[0]
    passed = max(0, month_index(start) - first_index)
    if passed < installment.number_of_installments and month_date(first_index + passed, installment.first_due_on.day) < start:
        passed += 1
    return installment.monthly_amount * 0, max(installment.number_of_installments - passed, 0)
