from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from pypdf import PdfReader

from dashboard.monthly import monthly_context
from .models import (BudgetPreference, Expense, Income, Installment, PersonalBudget,
                     RecurringExpense, SavingsAccount, SavingsMovement)
from .periods import period_bounds, period_month, installment_for_period
from .recurring import generate_recurring, pending_recurring
from .savings import savings_evolution


class BudgetPeriodTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="period-user")
        self.other = get_user_model().objects.create_user(username="other-period-user")
        self.preference = BudgetPreference.objects.create(owner=self.user, start_day=5)
        self.client.force_login(self.user)

    def test_boundaries_clamping_and_continuity(self):
        for month, day, start, end in [
            ("2026-10", 1, date(2026, 10, 1), date(2026, 10, 31)),
            ("2026-10", 5, date(2026, 10, 5), date(2026, 11, 4)),
            ("2026-01", 31, date(2026, 1, 31), date(2026, 2, 27)),
            ("2026-02", 31, date(2026, 2, 28), date(2026, 3, 30)),
            ("2028-02", 30, date(2028, 2, 29), date(2028, 3, 29)),
            ("2026-12", 5, date(2026, 12, 5), date(2027, 1, 4)),
            ("9999-12", 31, date(9999, 12, 31), date.max),
        ]:
            with self.subTest(month=month, day=day):
                self.assertEqual(period_bounds(month, day), (start, end))
        for day in (1, 5, 29, 30, 31):
            for month in range(1, 12):
                self.assertEqual(period_bounds(f"2028-{month:02d}", day)[1] + timedelta(days=1),
                                 period_bounds(f"2028-{month + 1:02d}", day)[0])

    def test_current_period_uses_user_boundary_and_defaults_to_calendar(self):
        self.assertEqual(period_month(self.user, date(2026, 11, 4)), "2026-10")
        self.assertEqual(period_month(self.user, date(2026, 11, 5)), "2026-11")
        self.assertEqual(period_month(self.other, date(2026, 11, 4)), "2026-11")
        with patch("finances.periods.timezone.localdate", return_value=date(2026, 11, 4)):
            for route in ("monthly-summary", "income-list", "expense-list", "installment-list",
                          "savings-list", "personal-budget", "monthly-report"):
                with self.subTest(route=route):
                    self.assertEqual(self.client.get(reverse(route)).context["selected_month"], "2026-10")

    def test_settings_validate_and_ignore_posted_owner(self):
        url = reverse("budget-settings")
        for invalid in ("0", "32", "text", ""):
            response = self.client.post(url, {"budget-settings-start_day": invalid})
            self.assertTrue(response.context["form"].errors)
            self.preference.refresh_from_db()
            self.assertEqual(self.preference.start_day, 5)
        response = self.client.post(url, {"budget-settings-start_day": "31", "owner": self.other.pk})
        self.assertEqual(response.status_code, 302)
        self.preference.refresh_from_db()
        self.assertEqual(self.preference.start_day, 31)
        self.assertFalse(BudgetPreference.objects.filter(owner=self.other).exists())

    def test_settings_require_login_csrf_and_get_does_not_write(self):
        url = reverse("budget-settings")
        self.assertEqual(Client().get(url).status_code, 302)
        secure = Client(enforce_csrf_checks=True)
        secure.force_login(self.user)
        self.assertEqual(secure.post(url, {"budget-settings-start_day": "10"}).status_code, 403)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertFalse(BudgetPreference.objects.filter(owner=self.other).exists())

    def test_summary_settings_modal_and_human_month_labels(self):
        response = self.client.get(reverse("monthly-summary"), {"month": "2026-10"})
        self.assertContains(response, 'id="budget-settings-modal"', count=1)
        self.assertContains(response, 'id="id_budget-settings-start_day"', count=1)
        self.assertContains(response, "Luna selectată: 2026-Oct")
        self.assertEqual(response.context["selected_month"], "2026-10")
        self.assertContains(response, '?month=2026-10')
        self.assertEqual(response.context["settings_form"]["start_day"].value(), 5)
        response = self.client.get(reverse("income-list"), {"month": "2027-01"})
        self.assertContains(response, "Luna selectată: 2027-Ian")

    def test_invalid_modal_setting_keeps_value_and_reopens_in_summary(self):
        response = self.client.post(reverse("budget-settings") + "?month=2026-10", {
            "in_modal": "1", "budget-settings-start_day": "32"})
        self.assertTemplateUsed(response, "dashboard/summary.html")
        self.assertEqual(response.context["settings_form"]["start_day"].value(), "32")
        self.assertTrue(response.context["settings_form"].errors)
        self.assertContains(response, 'data-has-errors="true"')
        self.assertEqual(response.context["selected_month"], "2026-10")
        self.preference.refresh_from_db()
        self.assertEqual(self.preference.start_day, 5)

    def populate(self):
        SavingsAccount.objects.create(owner=self.user, opening_balance=100, started_on=date(2026, 10, 1))
        for day in (date(2026, 10, 4), date(2026, 10, 5), date(2026, 11, 4), date(2026, 11, 5)):
            Income.objects.create(owner=self.user, source=f"Income-{day}", amount=1000, received_on=day)
            Expense.objects.create(owner=self.user, name=f"Expense-{day}", category="other", amount=100,
                                   paid_on=day, from_personal_budget=True)
            SavingsMovement.objects.create(owner=self.user, kind="deposit", amount=50, occurred_on=day)
        Income.objects.create(owner=self.other, source="SECRET", amount=9999, received_on=date(2026, 11, 1))
        Expense.objects.create(owner=self.other, name="SECRET", category="other", amount=9999, paid_on=date(2026, 11, 1))
        PersonalBudget.objects.create(owner=self.user, month=date(2026, 10, 1), amount=300)
        PersonalBudget.objects.create(owner=self.user, month=date(2026, 11, 1), amount=900)
        SavingsMovement.objects.create(owner=self.user, kind="withdrawal", amount=20, occurred_on=date(2026, 11, 2))
        Installment.objects.create(owner=self.user, name="Loan", monthly_amount=75,
                                   first_due_on=date(2026, 10, 1), number_of_installments=3)

    def test_shared_totals_include_both_edges_and_exclude_other_period_owner(self):
        self.populate()
        expected = {"income": 2000, "expenses": 275, "installment_total": 75,
                    "savings_balance": 230, "savings_deposits": 100, "savings_withdrawals": 20,
                    "personal_allocated": 300, "personal_spent": 200, "personal_remaining": 100,
                    "balance": 1645, "unallocated_balance": 1545}
        for route in ("monthly-summary", "monthly-report"):
            response = self.client.get(reverse(route), {"month": "2026-10"})
            for key, value in expected.items():
                with self.subTest(route=route, key=key):
                    self.assertEqual(response.context[key], Decimal(value))
            self.assertNotContains(response, "SECRET")

    def test_lists_and_graph_use_same_period(self):
        self.populate()
        for route, key, count in (("income-list", "incomes", 2), ("expense-list", "expenses", 2),
                                  ("savings-list", "movements", 3), ("personal-budget", "personal_expenses", 2)):
            response = self.client.get(reverse(route), {"month": "2026-10"})
            self.assertEqual(len(response.context[key]), count)
            self.assertEqual(response.context["period_end"], date(2026, 11, 4))
        points = savings_evolution(self.user, "2026-11")
        self.assertEqual([(p["month"], p["balance"]) for p in points],
                         [("2026-09", 150), ("2026-10", 230), ("2026-11", 280)])

    def test_pdf_has_explicit_range_and_only_period_records(self):
        self.populate()
        response = self.client.get(reverse("monthly-report-pdf"), {"month": "2026-10"})
        text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(response.content)).pages)
        for included in ("05.10.2026", "04.11.2026", "Income-2026-11-04", "1545,00 lei"):
            self.assertIn(included, text)
        for excluded in ("Income-2026-10-04", "Income-2026-11-05", "SECRET"):
            self.assertNotIn(excluded, text)

    def test_boundary_change_recomputes_without_mutating_records_or_allocations(self):
        self.populate()
        before = list(Income.objects.values_list("pk", "received_on", "amount"))
        self.client.post(reverse("budget-settings"), {"budget-settings-start_day": 1})
        context = monthly_context(self.user, "2026-10")
        self.assertEqual(context["personal_allocated"], 300)
        self.assertEqual(context["savings_balance"], 200)
        self.assertEqual(before, list(Income.objects.values_list("pk", "received_on", "amount")))
        self.assertEqual(PersonalBudget.objects.filter(owner=self.user).count(), 2)

    def test_creation_edit_and_deletion_redirect_to_containing_period(self):
        response = self.client.post(reverse("income-list"), {"source": "Salary", "amount": "100", "received_on": "2026-11-04"})
        self.assertRedirects(response, reverse("income-list") + "?month=2026-10")
        income = Income.objects.get(owner=self.user)
        response = self.client.post(reverse("income-edit", args=[income.pk]), {"source": "Salary", "amount": "100", "received_on": "2026-11-05"})
        self.assertRedirects(response, reverse("income-list") + "?month=2026-11")
        response = self.client.post(reverse("income-delete", args=[income.pk]))
        self.assertRedirects(response, reverse("income-list") + "?month=2026-11")

    def test_installments_follow_due_day_and_clamp(self):
        loan = Installment(monthly_amount=Decimal("75"), first_due_on=date(2026, 10, 1), number_of_installments=2)
        for month, expected in (("2026-09", (75, 2)), ("2026-10", (75, 1)), ("2026-11", (0, 0))):
            self.assertEqual(installment_for_period(loan, *period_bounds(month, 5)), expected)
        loan.first_due_on = date(2026, 1, 28)
        loan.number_of_installments = 3
        self.assertEqual(installment_for_period(loan, *period_bounds("2026-02", 31)), (150, 2))
        self.assertEqual(installment_for_period(loan, *period_bounds("2026-03", 31)), (0, 0))
        loan.first_due_on = date(2026, 1, 31)
        self.assertEqual(installment_for_period(loan, *period_bounds("2026-02", 5)), (75, 2))

    def test_expense_and_savings_redirects_follow_actual_date(self):
        response = self.client.post(reverse("expense-list"), {
            "name": "Purchase", "category": "other", "amount": "25", "paid_on": "2026-11-04"})
        self.assertRedirects(response, reverse("expense-list") + "?month=2026-10")
        SavingsAccount.objects.create(owner=self.user, opening_balance=0, started_on=date(2026, 10, 1))
        response = self.client.post(reverse("savings-list"), {
            "movement-kind": "deposit", "movement-amount": "100", "movement-occurred_on": "2026-11-04"})
        self.assertRedirects(response, reverse("savings-list") + "?month=2026-10")
        movement = SavingsMovement.objects.get(owner=self.user)
        response = self.client.post(reverse("savings-edit", args=[movement.pk]), {
            "edit-movement-kind": "deposit", "edit-movement-amount": "100",
            "edit-movement-occurred_on": "2026-11-05"})
        self.assertRedirects(response, reverse("savings-list") + "?month=2026-11")
        response = self.client.post(reverse("savings-delete", args=[movement.pk]))
        self.assertRedirects(response, reverse("savings-list") + "?month=2026-11")

    def test_empty_period_has_zero_totals_and_no_chart_before_account(self):
        SavingsAccount.objects.create(owner=self.user, opening_balance=100, started_on=date(2026, 11, 5))
        context = monthly_context(self.user, "2026-10")
        for key in ("income", "expenses", "unallocated_balance", "savings_balance", "personal_allocated"):
            self.assertEqual(context[key], 0)
        self.assertEqual(context["savings_evolution"], [])

    def test_recurring_generation_keeps_calendar_identity_after_boundary_change(self):
        for day in (1, 10):
            RecurringExpense.objects.create(owner=self.user, name=f"Bill-{day}", category="other", amount=10,
                                            payment_day=day, starts_on=date(2026, 10, 1))
        self.assertEqual([r["paid_on"] for r in pending_recurring(self.user, "2026-10")],
                         [date(2026, 10, 10), date(2026, 11, 1)])
        self.assertEqual(generate_recurring(self.user, "2026-10"), 2)
        self.assertEqual(generate_recurring(self.user, "2026-10"), 0)
        self.preference.start_day = 1
        self.preference.save()
        self.assertEqual(generate_recurring(self.user, "2026-11"), 1)
        self.assertEqual(Expense.objects.filter(paid_on=date(2026, 11, 1)).count(), 1)

    def test_long_period_can_contain_two_recurring_due_dates_without_duplicates(self):
        self.preference.start_day = 31
        self.preference.save()
        RecurringExpense.objects.create(owner=self.user, name="Bill", category="other", amount=10,
                                        payment_day=28, starts_on=date(2026, 1, 1))
        self.assertEqual(generate_recurring(self.user, "2026-02"), 2)
        self.assertEqual(generate_recurring(self.user, "2026-03"), 1)
        self.assertEqual(Expense.objects.filter(paid_on=date(2026, 4, 28)).count(), 1)
        self.assertEqual(generate_recurring(self.user, "2026-02"), 0)
