from datetime import date

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponseBadRequest
from django.urls import reverse
from django.views.decorators.http import require_POST

from dashboard.forms import MonthField
from .models import Expense, RecurringExpense, RecurringExpenseOccurrence
from .periods import budget_period, month_date, month_index


class RecurringExpenseForm(forms.ModelForm):
    starts_on = MonthField(label="Luna de început", widget=forms.TextInput(attrs={"type": "month"}))

    class Meta:
        model = RecurringExpense
        fields = ["name", "category", "amount", "payment_day", "starts_on", "active"]
        labels = {"name": "Nume", "category": "Categorie", "amount": "Sumă (lei)",
                  "payment_day": "Ziua plății (1–31)", "active": "Regulă activă"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial["starts_on"] = self.instance.starts_on.strftime("%Y-%m")

    def clean_starts_on(self):
        return date.fromisoformat(f"{self.cleaned_data['starts_on']}-01")


def pending_recurring(owner, selected_month):
    start, end = budget_period(owner, selected_month)
    pending = []
    for index in range(month_index(start), month_index(end) + 1):
        month = month_date(index)
        rules = RecurringExpense.objects.filter(owner=owner, active=True, starts_on__lte=month).exclude(
            pk__in=RecurringExpenseOccurrence.objects.filter(rule__owner=owner, month=month).values("rule_id"),
        ).order_by("name", "pk")
        for rule in rules:
            paid_on = month_date(index, rule.payment_day)
            if start <= paid_on <= end:
                pending.append({"rule": rule, "paid_on": paid_on, "occurrence_month": month})
    return sorted(pending, key=lambda row: (row["paid_on"], row["rule"].pk))


@transaction.atomic
def generate_recurring(owner, selected_month):
    count = 0
    for row in pending_recurring(owner, selected_month):
        rule = row["rule"]
        occurrence, created = RecurringExpenseOccurrence.objects.get_or_create(rule=rule, month=row["occurrence_month"])
        if not created:
            continue
        expense = Expense.objects.create(owner=owner, name=rule.name, category=rule.category,
                                         amount=rule.amount, paid_on=row["paid_on"])
        occurrence.expense = expense
        occurrence.save(update_fields=["expense"])
        count += 1
    return count


@login_required
def recurring_list(request, pk=None):
    rule = get_object_or_404(RecurringExpense, pk=pk, owner=request.user) if pk is not None else None
    form = RecurringExpenseForm(request.POST if request.method == "POST" else None,
                                instance=rule, prefix="recurring")
    if request.method == "POST" and form.is_valid():
        rule = form.save(commit=False)
        rule.owner = request.user
        rule.save()
        return redirect("recurring-list")
    return render(request, "finances/recurring_list.html", {
        "form": form, "editing": pk is not None,
        "rules": RecurringExpense.objects.filter(owner=request.user).order_by("name", "pk"),
    })


@login_required
@require_POST
def recurring_generate(request):
    try:
        month = MonthField().clean(request.POST.get("month", ""))
    except ValidationError:
        return HttpResponseBadRequest("Lună invalidă.")
    count = generate_recurring(request.user, month)
    messages.success(request, f"{count} cheltuieli recurente generate pentru {month}.")
    return redirect(f"{reverse('expense-list')}?month={month}")
