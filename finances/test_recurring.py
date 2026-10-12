from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Expense, RecurringExpense, RecurringExpenseOccurrence
from .recurring import RecurringExpenseForm, generate_recurring, pending_recurring


class RecurringTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="owner")
        self.other = get_user_model().objects.create_user(username="other")
        self.client.force_login(self.user)
        self.rule = RecurringExpense.objects.create(
            owner=self.user, name="Chirie", category="rent", amount=Decimal("1500.00"),
            payment_day=31, starts_on=date(2026, 1, 1),
        )

    def test_day_clamps_for_february_leap_year_and_thirty_day_month(self):
        for month, expected in [("2026-02", date(2026, 2, 28)), ("2028-02", date(2028, 2, 29)),
                                ("2026-04", date(2026, 4, 30)), ("2026-01", date(2026, 1, 31))]:
            self.assertEqual(generate_recurring(self.user, month), 1)
            self.assertTrue(Expense.objects.filter(owner=self.user, paid_on=expected).exists())

    def test_generation_is_repeatable_after_edit_or_delete_of_expense(self):
        self.assertEqual(generate_recurring(self.user, "2026-10"), 1)
        expense = Expense.objects.get()
        expense.amount = Decimal("1600.00")
        expense.paid_on = date(2026, 11, 1)
        expense.save()
        self.assertEqual(generate_recurring(self.user, "2026-10"), 0)
        expense.delete()
        self.assertEqual(generate_recurring(self.user, "2026-10"), 0)
        self.assertEqual(RecurringExpenseOccurrence.objects.count(), 1)
        self.assertFalse(Expense.objects.exists())

    def test_rule_changes_preserve_generated_history(self):
        generate_recurring(self.user, "2026-10")
        self.rule.amount = Decimal("1700.00")
        self.rule.name = "Chirie nouă"
        self.rule.save()
        generate_recurring(self.user, "2026-11")
        self.assertEqual(Expense.objects.get(paid_on__month=10).amount, Decimal("1500.00"))
        self.assertEqual(Expense.objects.get(paid_on__month=10).name, "Chirie")
        self.assertEqual(Expense.objects.get(paid_on__month=11).amount, Decimal("1700.00"))

    def test_inactive_future_and_other_user_rules_are_excluded(self):
        self.assertEqual(pending_recurring(self.user, "2025-12"), [])
        self.assertEqual(generate_recurring(self.other, "2026-10"), 0)
        self.rule.active = False
        self.rule.save()
        self.assertEqual(generate_recurring(self.user, "2026-10"), 0)

    def test_occurrence_database_constraint_prevents_duplicate(self):
        generate_recurring(self.user, "2026-10")
        with self.assertRaises(IntegrityError), transaction.atomic():
            RecurringExpenseOccurrence.objects.create(rule=self.rule, month=date(2026, 10, 1))

    def test_generation_requires_post_valid_month_and_login(self):
        url = "/finances/expenses/recurring/generate/"
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url, {"month": "2026-13"}).status_code, 400)
        response = self.client.post(url, {"month": "2026-10", "owner": self.other.pk})
        self.assertRedirects(response, "/finances/expenses/?month=2026-10")
        self.assertEqual(Expense.objects.get().owner, self.user)
        self.client.logout()
        self.assertEqual(self.client.post(url, {"month": "2026-10"}).status_code, 302)

    def test_forms_validate_amount_day_month_and_ignore_owner(self):
        data = {"recurring-name": "Internet", "recurring-category": "utilities",
                "recurring-amount": "65.00", "recurring-payment_day": "10",
                "recurring-starts_on": "2026-10", "recurring-active": "on", "owner": self.other.pk}
        self.assertRedirects(self.client.post("/finances/expenses/recurring/", data), "/finances/expenses/recurring/")
        self.assertEqual(RecurringExpense.objects.get(name="Internet").owner, self.user)
        for field, value in [("amount", "0"), ("amount", "-1"), ("payment_day", "0"),
                             ("payment_day", "32"), ("starts_on", "2026-13")]:
            invalid = dict(data, **{f"recurring-{field}": value})
            form = RecurringExpenseForm(invalid, prefix="recurring")
            self.assertFalse(form.is_valid())
            self.assertIn(field, form.errors)

    def test_rule_edit_access_is_scoped_to_owner(self):
        url = f"/finances/expenses/recurring/{self.rule.pk}/edit/"
        self.client.force_login(self.other)
        for method in ["get", "post"]:
            self.assertEqual(getattr(self.client, method)(url).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get("/finances/expenses/recurring/").status_code, 302)

    def test_owner_can_edit_and_deactivate_rule_without_changing_expenses(self):
        generate_recurring(self.user, "2026-10")
        url = f"/finances/expenses/recurring/{self.rule.pk}/edit/"
        response = self.client.get(url)
        self.assertContains(response, 'value="2026-01"')
        response = self.client.post(url, {
            "recurring-name": "Chirie corectată", "recurring-category": "rent",
            "recurring-amount": "1750.00", "recurring-payment_day": "15",
            "recurring-starts_on": "2026-01",
        })
        self.assertRedirects(response, "/finances/expenses/recurring/")
        self.rule.refresh_from_db()
        self.assertFalse(self.rule.active)
        self.assertEqual(self.rule.amount, Decimal("1750.00"))
        self.assertEqual(Expense.objects.get().amount, Decimal("1500.00"))
        self.assertEqual(generate_recurring(self.user, "2026-11"), 0)

    def test_preview_does_not_create_expenses_or_change_summary(self):
        response = self.client.get("/finances/expenses/?month=2026-10")
        self.assertContains(response, "Generează cheltuielile lunii")
        self.assertEqual(len(response.context["pending_recurring"]), 1)
        self.assertFalse(Expense.objects.exists())
        self.assertEqual(self.client.get("/dashboard/?month=2026-10").context["expenses"], Decimal("0.00"))
        generate_recurring(self.user, "2026-10")
        self.assertEqual(self.client.get("/dashboard/?month=2026-10").context["expenses"], Decimal("1500.00"))
        self.assertEqual(pending_recurring(self.user, "2026-10"), [])
