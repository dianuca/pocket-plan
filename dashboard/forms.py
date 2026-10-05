from datetime import date
from decimal import Decimal
import re

from django import forms


class MonthField(forms.CharField):
    def validate(self, value):
        super().validate(value)

        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}", value):
            raise forms.ValidationError("Folosește formatul YYYY-MM.")

        try:
            date.fromisoformat(f"{value}-01")
        except ValueError:
            raise forms.ValidationError("Luna selectată nu există.")


class InstallmentPreviewForm(forms.Form):
    name = forms.CharField(
        label="Numele ratei",
        max_length=100,
    )

    monthly_amount = forms.DecimalField(
        label="Suma lunară",
        min_value=Decimal("0.01"),
        max_digits=10,
        decimal_places=2,
    )

    first_month = MonthField(
        label="Luna primei scadențe",
        widget=forms.TextInput(attrs={"type": "month"}),
    )

    number_of_installments = forms.IntegerField(
        label="Numărul de rate",
        min_value=1,
    )

    selected_month = MonthField(
        label="Luna pentru previzualizare",
        widget=forms.TextInput(attrs={"type": "month"}),
    )