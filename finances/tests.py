from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Income


class IncomeModelTests(TestCase):
    def test_income_is_saved_with_its_owner(self):
        user = get_user_model().objects.create_user(
            username="testuser",
            password="TestPassword123!",
        )

        income = Income.objects.create(
            owner=user,
            source="Salariu",
            amount=Decimal("5000.00"),
            received_on=date(2026, 10, 5),
        )

        saved_income = Income.objects.get(pk=income.pk)

        self.assertEqual(saved_income.owner, user)
        self.assertEqual(saved_income.source, "Salariu")
        self.assertEqual(saved_income.amount, Decimal("5000.00"))
        self.assertEqual(saved_income.received_on, date(2026, 10, 5))