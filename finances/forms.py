from decimal import Decimal
from django import forms
from .models import Income
from .models import Expense, Income, Installment


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

class InstallmentForm(forms.ModelForm):
    class Meta:
        model = Installment
        fields = [
            "name",
            "monthly_amount",
            "first_due_on",
            "number_of_installments",
        ]

        labels = {
            "name": "Numele ratei",
            "monthly_amount": "Suma lunară",
            "first_due_on": "Prima scadență",
            "number_of_installments": "Numărul total de rate",
        }

        widgets = {
            "first_due_on": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),
        }
