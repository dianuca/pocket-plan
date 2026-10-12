from datetime import date
from decimal import Decimal

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse

from dashboard.forms import MonthField
from .models import Expense, PersonalBudget


class PersonalBudgetForm(forms.Form):
    amount = forms.DecimalField(label="Buget alocat pentru luna aceasta (lei)",
                                min_value=Decimal("0.00"), max_digits=12, decimal_places=2,
                                help_text="Suma este rezervată pentru tine. Poți seta 0 pentru a elibera alocarea.")


def personal_expenses(owner, month):
    return Expense.objects.filter(owner=owner, from_personal_budget=True,
                                  paid_on__year=month.year, paid_on__month=month.month)


def personal_budget_summary(owner, selected_month):
    month = date.fromisoformat(f"{selected_month}-01")
    allocation = PersonalBudget.objects.filter(owner=owner, month=month).first()
    allocated = allocation.amount if allocation else Decimal("0.00")
    spent = personal_expenses(owner, month).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    remaining = allocated - spent
    return {"personal_allocated": allocated, "personal_spent": spent,
            "personal_remaining": remaining,
            "personal_reserved": max(remaining, Decimal("0.00")),
            "personal_overspent": max(-remaining, Decimal("0.00"))}


@login_required
def personal_budget_list(request):
    try:
        selected_month = MonthField().clean(request.GET.get("month", date.today().strftime("%Y-%m")))
    except ValidationError:
        return HttpResponseBadRequest("Lună invalidă.")
    month = date.fromisoformat(f"{selected_month}-01")
    summary = personal_budget_summary(request.user, selected_month)
    form = PersonalBudgetForm(request.POST if request.method == "POST" else None,
                              prefix="personal", initial={"amount": summary["personal_allocated"]})
    if request.method == "POST" and form.is_valid():
        PersonalBudget.objects.update_or_create(owner=request.user, month=month,
                                                defaults={"amount": form.cleaned_data["amount"]})
        return redirect(f"{reverse('personal-budget')}?month={selected_month}")
    return render(request, "finances/personal_budget.html", {
        **summary,
        "selected_month": selected_month, "form": form,
        "personal_expenses": personal_expenses(request.user, month).order_by("-paid_on", "-pk"),
    })
