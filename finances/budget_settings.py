from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from dashboard.forms import MonthField
from django.core.exceptions import ValidationError
from django.http import HttpResponseBadRequest

from .models import BudgetPreference
from .periods import period_context, period_month, start_day_for


class BudgetPreferenceForm(forms.Form):
    start_day = forms.IntegerField(label="Ziua în care începe luna ta", min_value=1, max_value=31,
                                  help_text="1 = lună calendaristică. Pentru zile inexistente se folosește ultima zi din lună.")


@login_required
def budget_settings(request):
    form = BudgetPreferenceForm(request.POST if request.method == "POST" else None,
                                prefix="budget-settings", initial={"start_day": start_day_for(request.user)})
    if request.method == "POST" and form.is_valid():
        BudgetPreference.objects.update_or_create(owner=request.user, defaults={"start_day": form.cleaned_data["start_day"]})
        return redirect(f"{reverse('monthly-summary')}?month={period_month(request.user)}")
    month = period_month(request.user)
    if request.method == "POST" and request.POST.get("in_modal") == "1":
        from dashboard.monthly import monthly_context

        try:
            month = MonthField().clean(request.GET.get("month", month))
        except ValidationError:
            return HttpResponseBadRequest("Lună invalidă.")
        return render(request, "dashboard/summary.html", {
            **monthly_context(request.user, month), "settings_form": form,
        })
    return render(request, "finances/budget_settings.html", {
        "form": form, **period_context(request.user, month),
    })
