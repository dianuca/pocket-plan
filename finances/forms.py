from decimal import Decimal
from django import forms
from .models import Income
from .models import Expense, Income


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

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["name", "category", "amount", "paid_on"]

        labels = {
            "name": "Numele cheltuielii",
            "category": "Categorie",
            "amount": "Sumă",
            "paid_on": "Data plății",
        }

        widgets = {
            "paid_on": forms.DateInput(
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
