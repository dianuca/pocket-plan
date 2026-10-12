from datetime import date
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase

from .models import Expense, Income, Installment, SavingsAccount, SavingsMovement


class SeedDemoTests(TestCase):
    def test_multiple_savings_months_cross_year_and_remain_repeatable(self):
        demo = get_user_model().objects.create_user(username="pocketplan_demo")
        for _ in range(2):
            call_command("seed_demo", month="2027-02", savings=True, months=4, stdout=StringIO())
        account = SavingsAccount.objects.get(owner=demo)
        self.assertEqual(account.started_on, date(2026, 11, 1))
        self.assertEqual(SavingsMovement.objects.filter(owner=demo).count(), 12)
        self.client.force_login(demo)
        response = self.client.get("/finances/savings/?month=2027-02")
        self.assertEqual(response.context["savings_balance"], Decimal("-1300.00"))
        self.assertEqual(len(response.context["savings_evolution"]), 4)

    def test_invalid_month_count_creates_no_records(self):
        for count in [0, -1, 121]:
            with self.assertRaises(CommandError):
                call_command("seed_demo", savings=True, months=count, stdout=StringIO())
        self.assertFalse(get_user_model().objects.exists())

    def test_savings_seed_is_repeatable_and_integrates_with_budget(self):
        demo = get_user_model().objects.create_user(username="pocketplan_demo")
        for _ in range(2):
            call_command("seed_demo", month="2026-10", savings=True, stdout=StringIO())
        self.assertEqual(SavingsAccount.objects.filter(owner=demo).count(), 1)
        self.assertEqual(SavingsMovement.objects.filter(owner=demo).count(), 3)
        self.client.force_login(demo)
        response = self.client.get("/dashboard/?month=2026-10")
        self.assertEqual(response.context["savings_balance"], Decimal("-100.00"))
        self.assertEqual(response.context["savings_deficit"], Decimal("100.00"))
        self.assertEqual(response.context["balance"], Decimal("4713.50"))

    def test_savings_seed_preserves_existing_account_and_skips_earlier_dates(self):
        demo = get_user_model().objects.create_user(username="pocketplan_demo")
        account = SavingsAccount.objects.create(
            owner=demo, opening_balance=Decimal("123.45"), started_on=date(2026, 11, 1),
        )
        call_command("seed_demo", month="2026-10", savings=True, stdout=StringIO())
        account.refresh_from_db()
        self.assertEqual(account.opening_balance, Decimal("123.45"))
        self.assertEqual(account.started_on, date(2026, 11, 1))
        self.assertFalse(SavingsMovement.objects.exists())

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
