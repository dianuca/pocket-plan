from calendar import monthrange
from datetime import date
from decimal import Decimal

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Sum
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from dashboard.forms import MonthField
from .models import SavingsAccount, SavingsMovement


class SavingsAccountForm(forms.ModelForm):
    def clean_started_on(self):
        started_on = self.cleaned_data["started_on"]
        if self.instance.pk and SavingsMovement.objects.filter(
            owner=self.instance.owner, occurred_on__lt=started_on,
        ).exists():
            raise forms.ValidationError("Data de început nu poate fi după un transfer existent.")
        return started_on

    class Meta:
        model = SavingsAccount
        fields = ["opening_balance", "started_on"]
        labels = {"opening_balance": "Sold inițial (lei)", "started_on": "Data de început"}
        widgets = {"started_on": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})}


class SavingsHistoryForm(forms.Form):
    start = forms.DateField(label="De la", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    end = forms.DateField(label="Până la", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    kind = forms.ChoiceField(label="Tip", required=False, choices=[("", "Toate"), *SavingsMovement.Kind.choices])

    def clean(self):
        data = super().clean()
        if data.get("start") and data.get("end") and data["start"] > data["end"]:
            raise forms.ValidationError("Data de început trebuie să fie înaintea datei de sfârșit.")
        return data


@login_required
def savings_history(request):
    form = SavingsHistoryForm(request.GET)
    rows = []
    account = SavingsAccount.objects.filter(owner=request.user).first()
    if form.is_valid() and account:
        balance = account.opening_balance
        filters = form.cleaned_data
        for movement in SavingsMovement.objects.filter(
            owner=request.user, occurred_on__gte=account.started_on,
        ).order_by("occurred_on", "pk"):
            balance += movement.amount if movement.kind == SavingsMovement.Kind.DEPOSIT else -movement.amount
            if filters.get("start") and movement.occurred_on < filters["start"]:
                continue
            if filters.get("end") and movement.occurred_on > filters["end"]:
                continue
            if filters.get("kind") and movement.kind != filters["kind"]:
                continue
            rows.append({"movement": movement, "balance": balance})
    rows.reverse()
    query = request.GET.copy()
    query.pop("page", None)
    template = "finances/savings_history.html"
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        template = "finances/includes/savings_history_content.html"
    return render(request, template, {
        "filter_form": form, "page_obj": Paginator(rows, 25).get_page(request.GET.get("page")),
        "filter_query": query.urlencode(), "account": account,
    })


class SavingsMovementForm(forms.ModelForm):
    class Meta:
        model = SavingsMovement
        fields = ["kind", "amount", "occurred_on", "description"]
        labels = {"kind": "Tip", "amount": "Sumă (lei)",
                  "occurred_on": "Data", "description": "Descriere"}
        widgets = {"occurred_on": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})}

    def __init__(self, *args, account, **kwargs):
        super().__init__(*args, **kwargs)
        self.account = account

    def clean_occurred_on(self):
        value = self.cleaned_data["occurred_on"]
        if value < self.account.started_on:
            raise forms.ValidationError("Data trebuie să fie începând cu data inițială a economiilor.")
        return value


def savings_summary(owner, selected_month):
    year, month = map(int, selected_month.split("-"))
    end = date(year, month, monthrange(year, month)[1])
    account = SavingsAccount.objects.filter(owner=owner).first()
    zero = Decimal("0.00")
    result = {"savings_balance": zero, "savings_deposits": zero,
              "savings_withdrawals": zero, "savings_deficit": zero}
    if account is None or account.started_on > end:
        return result
    movements = SavingsMovement.objects.filter(
        owner=owner, occurred_on__gte=account.started_on, occurred_on__lte=end,
    )
    totals = dict(movements.values("kind").annotate(total=Sum("amount"))
                  .values_list("kind", "total"))
    monthly = dict(movements.filter(occurred_on__year=year, occurred_on__month=month)
                   .values("kind").annotate(total=Sum("amount"))
                   .values_list("kind", "total"))
    balance = account.opening_balance + totals.get("deposit", zero) - totals.get("withdrawal", zero)
    result.update(savings_balance=balance, savings_deposits=monthly.get("deposit", zero),
                  savings_withdrawals=monthly.get("withdrawal", zero),
                  savings_deficit=max(-balance, zero))
    return result


@login_required
def savings_list(request):
    try:
        selected_month = MonthField().clean(request.GET.get("month", date.today().strftime("%Y-%m")))
    except ValidationError:
        return HttpResponseBadRequest("Lună invalidă.")
    account = SavingsAccount.objects.filter(owner=request.user).first()
    if account is None:
        form = SavingsAccountForm(
            request.POST if request.method == "POST" else None,
            prefix="opening", initial={"opening_balance": "0.00", "started_on": f"{selected_month}-01"},
        )
    else:
        form = SavingsMovementForm(
            request.POST if request.method == "POST" else None, account=account,
            prefix="movement", initial={"occurred_on": f"{selected_month}-01"},
        )
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.owner = request.user
        record.save()
        month = (record.started_on if account is None else record.occurred_on).strftime("%Y-%m")
        return redirect(f"{reverse('savings-list')}?month={month}")
    year, month = map(int, selected_month.split("-"))
    movements = SavingsMovement.objects.filter(
        owner=request.user, occurred_on__year=year, occurred_on__month=month,
    ).order_by("-occurred_on", "-pk")
    return render(request, "finances/savings_list.html", {
        "account": account, "form": form, "movements": movements,
        "selected_month": selected_month, "savings_evolution": savings_evolution(request.user, selected_month),
        **savings_summary(request.user, selected_month),
    })


def savings_evolution(owner, selected_month):
    account = SavingsAccount.objects.filter(owner=owner).first()
    if account is None:
        return []
    year, month = map(int, selected_month.split("-"))
    end_index = (year - 1) * 12 + month - 1
    start_index = max(0, end_index - 11, (account.started_on.year - 1) * 12 + account.started_on.month - 1)
    points = []
    balance = account.opening_balance
    movements = iter(SavingsMovement.objects.filter(
        owner=owner, occurred_on__gte=account.started_on,
        occurred_on__lte=date(year, month, monthrange(year, month)[1]),
    ).order_by("occurred_on", "pk"))
    movement = next(movements, None)
    for index in range(start_index, end_index + 1):
        point_year, point_month = divmod(index, 12)
        end = date(point_year + 1, point_month + 1, monthrange(point_year + 1, point_month + 1)[1])
        while movement is not None and movement.occurred_on <= end:
            balance += movement.amount if movement.kind == SavingsMovement.Kind.DEPOSIT else -movement.amount
            movement = next(movements, None)
        points.append({"month": end.strftime("%Y-%m"), "balance": balance})
    scale = max((abs(point["balance"]) for point in points), default=Decimal("0.00"))
    for point in points:
        point["height"] = int(abs(point["balance"]) / scale * 100) if scale else 0
    return points


@login_required
def savings_edit(request, pk):
    movement = get_object_or_404(SavingsMovement, pk=pk, owner=request.user)
    account = get_object_or_404(SavingsAccount, owner=request.user)
    form = SavingsMovementForm(
        request.POST if request.method == "POST" else None,
        instance=movement, account=account, prefix="edit-movement",
    )
    if request.method == "POST" and form.is_valid():
        movement = form.save()
        return redirect(f"{reverse('savings-list')}?month={movement.occurred_on:%Y-%m}")
    template = "finances/savings_action.html"
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        template = "finances/includes/savings_action_form.html"
    return render(request, template, {
        "form": form, "movement": movement, "deleting": False,
        "cancel_url": f"{reverse('savings-list')}?month={movement.occurred_on:%Y-%m}",
    })


@login_required
def savings_account_edit(request):
    account = get_object_or_404(SavingsAccount, owner=request.user)
    form = SavingsAccountForm(
        request.POST if request.method == "POST" else None,
        instance=account, prefix="edit-opening",
    )
    if request.method == "POST" and form.is_valid():
        account = form.save()
        return redirect(f"{reverse('savings-list')}?month={account.started_on:%Y-%m}")
    template = "finances/savings_action.html"
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        template = "finances/includes/savings_action_form.html"
    return render(request, template, {
        "form": form, "editing_account": True,
        "cancel_url": f"{reverse('savings-list')}?month={account.started_on:%Y-%m}",
    })


@login_required
def savings_delete(request, pk):
    movement = get_object_or_404(SavingsMovement, pk=pk, owner=request.user)
    cancel_url = f"{reverse('savings-list')}?month={movement.occurred_on:%Y-%m}"
    if request.method == "POST":
        movement.delete()
        return redirect(cancel_url)
    template = "finances/savings_action.html"
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        template = "finances/includes/savings_action_form.html"
    return render(request, template, {
        "movement": movement, "deleting": True, "cancel_url": cancel_url,
    })
