from decimal import Decimal
from django import forms
from .models import Income


class IncomeForm(forms.ModelForm):
    class Meta:
        model = Income
        fields = ["source", "amount", "received_on"]
        labels = {
            "source": "Sursa venitului",
            "amount": "Sumă",
            "received_on": "Data încasării",
        }
        widgets = {
            "received_on": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),
        }

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= Decimal("0.00"):
            raise forms.ValidationError(
                "Suma trebuie să fie mai mare decât zero."
            )
        return amount

