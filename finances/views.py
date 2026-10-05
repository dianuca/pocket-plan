from datetime import date
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from dashboard.forms import MonthField
from django.shortcuts import get_object_or_404, redirect, render
from django.core.exceptions import ValidationError
from .forms import ExpenseForm, IncomeForm, InstallmentForm
from .models import Expense, Income, Installment
from dashboard.services import (
    installment_amount_for_month,
    remaining_installments,
) 


@login_required
def income_list(request):
    selected_month = request.GET.get(
        "month",
        date.today().strftime("%Y-%m"),
    )

    try:
        selected_month = MonthField().clean(selected_month)
    except ValidationError:
        return HttpResponseBadRequest("Lună invalidă.")

    if request.method == "POST":
        form = IncomeForm(data=request.POST)

        if form.is_valid():
            income = form.save(commit=False)
            income.owner = request.user
            income.save()

            month = income.received_on.strftime("%Y-%m")
            url = reverse("income-list")
            return redirect(f"{url}?month={month}")
    else:
        form = IncomeForm(initial={
            "received_on": date.fromisoformat(f"{selected_month}-01"),
        })

    year, month = map(int, selected_month.split("-"))

    incomes = Income.objects.filter(
        owner=request.user,
        received_on__year=year,
        received_on__month=month,
    ).order_by("-received_on", "-pk")

    return render(
        request,
        "finances/income_list.html",
        {
            "form": form,
            "incomes": incomes,
            "selected_month": selected_month,
        },
    )

@login_required
def income_edit(request, pk):
    income = get_object_or_404(
        Income,
        pk=pk,
        owner=request.user,
    )

    if request.method == "POST":
        form = IncomeForm(data=request.POST, instance=income)

        if form.is_valid():
            income = form.save()

            month = income.received_on.strftime("%Y-%m")
            url = reverse("income-list")
            return redirect(f"{url}?month={month}")
    else:
        form = IncomeForm(instance=income)

    return render(
        request,
        "finances/income_edit.html",
        {"form": form, "income": income},
    )

@login_required
def income_delete(request, pk):
    income = get_object_or_404(
        Income,
        pk=pk,
        owner=request.user,
    )

    month = income.received_on.strftime("%Y-%m")
    cancel_url = f"{reverse('income-list')}?month={month}"

    if request.method == "POST":
        income.delete()
        return redirect(cancel_url)

    return render(
        request,
        "finances/income_confirm_delete.html",
        {
            "income": income,
            "cancel_url": cancel_url,
        },
    )

@login_required
def expense_list(request):
    selected_month = request.GET.get(
        "month",
        date.today().strftime("%Y-%m"),
    )

    try:
        selected_month = MonthField().clean(selected_month)
    except ValidationError:
        return HttpResponseBadRequest("Lună invalidă.")

    if request.method == "POST":
        form = ExpenseForm(data=request.POST)

        if form.is_valid():
            expense = form.save(commit=False)
            expense.owner = request.user
            expense.save()

            month = expense.paid_on.strftime("%Y-%m")
            url = reverse("expense-list")
            return redirect(f"{url}?month={month}")
    else:
        form = ExpenseForm(initial={
            "paid_on": date.fromisoformat(f"{selected_month}-01"),
        })

    year, month = map(int, selected_month.split("-"))

    expenses = Expense.objects.filter(
        owner=request.user,
        paid_on__year=year,
        paid_on__month=month,
    ).order_by("-paid_on", "-pk")

    return render(
        request,
        "finances/expense_list.html",
        {
            "form": form,
            "expenses": expenses,
            "selected_month": selected_month,
        },
    )

@login_required
def expense_edit(request, pk):
    expense = get_object_or_404(
        Expense,
        pk=pk,
        owner=request.user,
    )

    if request.method == "POST":
        form = ExpenseForm(data=request.POST, instance=expense)

        if form.is_valid():
            expense = form.save()

            month = expense.paid_on.strftime("%Y-%m")
            url = reverse("expense-list")
            return redirect(f"{url}?month={month}")
    else:
        form = ExpenseForm(instance=expense)

    return render(
        request,
        "finances/expense_edit.html",
        {"form": form, "expense": expense},
    )

@login_required
def expense_delete(request, pk):
    expense = get_object_or_404(
        Expense,
        pk=pk,
        owner=request.user,
    )

    month = expense.paid_on.strftime("%Y-%m")
    cancel_url = f"{reverse('expense-list')}?month={month}"

    if request.method == "POST":
        expense.delete()
        return redirect(cancel_url)

    return render(
        request,
        "finances/expense_confirm_delete.html",
        {
            "expense": expense,
            "cancel_url": cancel_url,
        },
    )

@login_required
def installment_list(request):
    selected_month = request.GET.get(
        "month",
        date.today().strftime("%Y-%m"),
    )

    try:
        selected_month = MonthField().clean(selected_month)
    except ValidationError:
        return HttpResponseBadRequest("Lună invalidă.")

    if request.method == "POST":
        form = InstallmentForm(data=request.POST)

        if form.is_valid():
            installment = form.save(commit=False)
            installment.owner = request.user
            installment.save()

            month = installment.first_due_on.strftime("%Y-%m")
            url = reverse("installment-list")
            return redirect(f"{url}?month={month}")
    else:
        form = InstallmentForm(initial={
            "first_due_on": date.fromisoformat(f"{selected_month}-01"),
        })

    installments = Installment.objects.filter(
        owner=request.user,
    ).order_by("name", "pk")

    installment_rows = []

    for installment in installments:
        first_month = installment.first_due_on.strftime("%Y-%m")

        installment_rows.append({
            "installment": installment,
            "amount_due": installment_amount_for_month(
                monthly_amount=installment.monthly_amount,
                first_month=first_month,
                number_of_installments=installment.number_of_installments,
                selected_month=selected_month,
            ),
            "remaining": remaining_installments(
                first_month=first_month,
                number_of_installments=installment.number_of_installments,
                selected_month=selected_month,
            ),
        })

    return render(
        request,
        "finances/installment_list.html",
        {
            "form": form,
            "installment_rows": installment_rows,
            "selected_month": selected_month,
        },
    )

@login_required
def installment_edit(request, pk):
    installment = get_object_or_404(
        Installment,
        pk=pk,
        owner=request.user,
    )

    if request.method == "POST":
        form = InstallmentForm(
            data=request.POST,
            instance=installment,
        )

        if form.is_valid():
            installment = form.save()

            month = installment.first_due_on.strftime("%Y-%m")
            url = reverse("installment-list")
            return redirect(f"{url}?month={month}")
    else:
        form = InstallmentForm(instance=installment)

    return render(
        request,
        "finances/installment_edit.html",
        {"form": form, "installment": installment},
    )

