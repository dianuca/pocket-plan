from datetime import date
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase

from .models import Expense, Income, Installment


class SeedDemoTests(TestCase):
    @patch("finances.management.commands.seed_demo.getpass", return_value="Demo-test-password123!")
    def test_repeat_run_preserves_users_and_does_not_duplicate_data(self, prompt):
        owner = get_user_model().objects.create_user(username="owner")
        original = Expense.objects.create(
            owner=owner, name="Cheltuială personală", category=Expense.Category.FOOD,
            amount=Decimal("42.00"), paid_on=date(2026, 10, 1),
        )
        for _ in range(2):
            call_command("seed_demo", month="2026-10", stdout=StringIO())

        demo = get_user_model().objects.get(username="pocketplan_demo")
        self.assertTrue(demo.check_password("Demo-test-password123!"))
        self.assertEqual(prompt.call_count, 1)
        self.assertEqual(Income.objects.filter(owner=demo).count(), 2)
        self.assertEqual(Expense.objects.filter(owner=demo).count(), 8)
        self.assertEqual(Installment.objects.filter(owner=demo).count(), 1)
        original.refresh_from_db()
        self.assertEqual(original.amount, Decimal("42.00"))
        self.client.force_login(demo)
        response = self.client.get("/dashboard/", {"month": "2026-10"})
        self.assertEqual(response.context["income"], Decimal("7350.00"))
        self.assertEqual(response.context["expenses"], Decimal("3036.50"))
        self.assertEqual(len(response.context["expenses_by_category"]), 7)

    def test_invalid_month_creates_no_user(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo", month="2026-13", stdout=StringIO())
        self.assertFalse(get_user_model().objects.exists())

    @patch("finances.management.commands.seed_demo.getpass", return_value="")
    def test_empty_password_rolls_back_new_account(self, prompt):
        with self.assertRaises(CommandError):
            call_command("seed_demo", month="2026-10", stdout=StringIO())
        self.assertFalse(get_user_model().objects.exists())
