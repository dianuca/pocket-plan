from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .models import Expense, Income, Installment, PersonalBudget, SavingsAccount, SavingsMovement
from dashboard.monthly import monthly_context


class PersonalBudgetTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="diana")
        self.other = get_user_model().objects.create_user(username="other")
        self.client.force_login(self.user)
        self.url = "/finances/personal-budget/?month=2026-10"

    def expense(self, amount="200.00", **kwargs):
        data = dict(owner=self.user, name="Carte", category="other", amount=Decimal(amount),
                    paid_on=date(2026, 10, 3), from_personal_budget=True)
        data.update(kwargs)
        return Expense.objects.create(**data)

    def test_manual_allocation_updates_existing_row_and_preserves_owner_month(self):
        allocation = PersonalBudget.objects.create(owner=self.user, month=date(2026, 10, 1), amount=Decimal("500"))
        response = self.client.get(self.url)
        self.assertEqual(response.context["personal_remaining"], Decimal("500"))
        self.assertContains(response, "Modifică alocarea")
        self.assertNotContains(response, "Cum funcționează")
        response = self.client.post(self.url, {"personal-amount": "999", "owner": self.other.pk, "month": "2026-09"})
        self.assertRedirects(response, self.url)
        allocation.refresh_from_db()
        self.assertEqual(allocation.amount, Decimal("999"))
        self.assertEqual(allocation.owner, self.user)
        self.assertEqual(allocation.month, date(2026, 10, 1))
        self.assertEqual(PersonalBudget.objects.count(), 1)
        for month in ["2026-13", "invalid", "", "0000-01"]:
            self.assertEqual(self.client.get("/finances/personal-budget/", {"month": month}).status_code, 400)

    def test_scoping_empty_month_no_rollover_and_read_only_get(self):
        PersonalBudget.objects.create(owner=self.user, month=date(2026, 10, 1), amount=Decimal("500"))
        PersonalBudget.objects.create(owner=self.other, month=date(2026, 10, 1), amount=Decimal("9999"))
        self.expense()
        self.expense("999", owner=self.other, name="Cheltuială străină")
        self.expense("999", paid_on=date(2026, 9, 3), name="Luna trecută")
        self.expense("999", from_personal_budget=False, name="Cheltuială obișnuită")
        response = self.client.get(self.url)
        self.assertEqual(response.context["personal_remaining"], Decimal("300.00"))
        for text in ["Cheltuială străină", "Luna trecută", "Cheltuială obișnuită"]:
            self.assertNotContains(response, text)
        response = self.client.get("/finances/personal-budget/?month=2026-11")
        self.assertEqual(response.context["personal_allocated"], Decimal("0.00"))
        self.assertEqual(response.context["personal_spent"], Decimal("0.00"))
        self.assertContains(response, "Nu există cheltuieli personale")
        self.assertEqual(PersonalBudget.objects.count(), 2)

    def test_summary_avoids_double_counting_with_savings_and_installments(self):
        PersonalBudget.objects.create(owner=self.user, month=date(2026, 10, 1), amount=Decimal("500"))
        self.expense()
        self.expense("1000", from_personal_budget=False)
        Income.objects.create(owner=self.user, source="Salariu", amount=Decimal("5000"), received_on=date(2026, 10, 1))
        Installment.objects.create(owner=self.user, name="Laptop", monthly_amount=Decimal("300"), first_due_on=date(2026, 10, 1), number_of_installments=3)
        SavingsAccount.objects.create(owner=self.user, opening_balance=Decimal("0"), started_on=date(2026, 10, 1))
        for kind, amount in [("deposit", "400"), ("withdrawal", "100")]:
            SavingsMovement.objects.create(owner=self.user, kind=kind, amount=Decimal(amount), occurred_on=date(2026, 10, 2))
        response = self.client.get("/dashboard/?month=2026-10")
        self.assertEqual(response.context["expenses"], Decimal("1500"))
        self.assertEqual(response.context["balance"], Decimal("3200"))
        self.assertEqual(response.context["personal_allocated"], Decimal("500"))
        self.assertEqual(response.context["personal_remaining"], Decimal("300"))
        self.assertEqual(response.context["unallocated_balance"], Decimal("2900"))
        html = response.content.decode()
        card = html.split('class="summary-card balance-card"')[1].split('</article>')[0]
        self.assertIn("Bani disponibili", card)
        self.assertIn("2900.00 lei", card)
        self.assertNotIn("3200.00 lei", card)
        self.assertEqual(response.context["direct_expenses"], Decimal("1200"))
        personal = self.client.get(self.url)
        for key in ["personal_allocated", "personal_remaining", "personal_spent"]:
            self.assertEqual(response.context[key], personal.context[key])
        self.expense("400")
        response = self.client.get("/dashboard/?month=2026-10")
        self.assertEqual(response.context["personal_remaining"], Decimal("-100"))
        self.assertEqual(response.context["personal_overspent"], Decimal("100"))
        self.assertEqual(response.context["unallocated_balance"], response.context["balance"])

    def test_allocation_validation_preserves_values_and_zero_keeps_expenses(self):
        self.client.post(self.url, {"personal-amount": "500"})
        expense = self.expense()
        for amount in ["-1", "abc", "1.001", "10000000000.00", ""]:
            response = self.client.post(self.url, {"personal-amount": amount})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors)
            self.assertEqual(response.context["form"]["amount"].value(), amount)
            self.assertContains(response, 'data-has-errors="true"')
            self.assertEqual(PersonalBudget.objects.get().amount, Decimal("500"))
        self.client.post(self.url, {"personal-amount": "0"})
        self.assertTrue(Expense.objects.filter(pk=expense.pk).exists())
        self.assertEqual(monthly_context(self.user, "2026-10")["personal_remaining"], Decimal("-200"))

    def test_expense_creation_edit_move_unmark_and_delete_recalculate(self):
        data = {"name": "Carte", "category": "other", "amount": "200", "paid_on": "2026-10-03", "from_personal_budget": "on", "owner": self.other.pk}
        response = self.client.post("/finances/expenses/?month=2026-10", data)
        self.assertEqual(response.status_code, 302)
        expense = Expense.objects.get()
        self.assertEqual(expense.owner, self.user)
        self.assertTrue(expense.from_personal_budget)
        data.update(amount="700", paid_on="2026-11-03")
        self.client.post(f"/finances/expenses/{expense.pk}/edit/", data)
        self.assertEqual(monthly_context(self.user, "2026-10")["personal_spent"], Decimal("0"))
        self.assertEqual(monthly_context(self.user, "2026-11")["personal_remaining"], Decimal("-700"))
        data.pop("from_personal_budget")
        self.client.post(f"/finances/expenses/{expense.pk}/edit/", data)
        self.assertEqual(monthly_context(self.user, "2026-11")["personal_spent"], Decimal("0"))
        data.update(paid_on="2026-10-03", from_personal_budget="on")
        self.client.post(f"/finances/expenses/{expense.pk}/edit/", data)
        self.client.post(f"/finances/expenses/{expense.pk}/delete/")
        self.assertEqual(monthly_context(self.user, "2026-10")["personal_remaining"], Decimal("0"))

    def test_summary_expense_footer_and_final_cards(self):
        self.expense("123.45")
        Installment.objects.create(owner=self.user, name="Laptop", monthly_amount=Decimal("300"),
                                   first_due_on=date(2026, 10, 1), number_of_installments=3)
        response = self.client.get("/dashboard/?month=2026-10")
        self.assertEqual(response.context["direct_expenses"], Decimal("123.45"))
        self.assertEqual(response.context["expenses"], Decimal("423.45"))
        html = response.content.decode()
        self.assertEqual(html.count('id="personal-budget-title"'), 1)
        title = html.split("<title>")[1].split("</title>")[0]
        self.assertEqual(title, "Rezumat lunar | PocketPlan")
        self.assertLess(html.index('aria-label="Lista cheltuielilor lunii"'), html.index("Total cheltuieli (fără rate):"))
        self.assertLess(html.index("Total cheltuieli (fără rate):"), html.index("Ratele lunii"))
        self.assertLess(html.index("Total rate:"), html.index('id="personal-budget-title"'))

    def test_access_csrf_and_escaping(self):
        self.expense(name="<script>demo</script>")
        self.assertContains(self.client.get(self.url), "&lt;script&gt;demo&lt;/script&gt;")
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.assertEqual(csrf_client.post(self.url, {"personal-amount": "100"}).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.assertEqual(self.client.post(self.url, {"personal-amount": "100"}).status_code, 302)
        self.assertEqual(PersonalBudget.objects.count(), 0)

    def test_summary_savings_chart_is_scoped_historical_and_handles_empty_data(self):
        response = self.client.get("/dashboard/?month=2026-10")
        self.assertContains(response, "Buget pentru mine")
        self.assertContains(response, "Nu există solduri pentru perioada selectată")
        self.assertNotContains(response, "Economii: depuneri")
        for owner in [self.user, self.other]:
            SavingsAccount.objects.create(owner=owner, opening_balance=Decimal("100"), started_on=date(2026, 9, 1))
        for owner, occurred_on, amount in [
            (self.user, date(2026, 9, 3), "200"),
            (self.user, date(2026, 10, 3), "300"),
            (self.user, date(2026, 11, 3), "900"),
            (self.other, date(2026, 10, 3), "9999"),
        ]:
            SavingsMovement.objects.create(owner=owner, occurred_on=occurred_on, amount=Decimal(amount), kind="deposit")
        response = self.client.get("/dashboard/?month=2026-10")
        self.assertEqual([(point["month"], point["balance"]) for point in response.context["savings_evolution"]],
                         [("2026-09", Decimal("300")), ("2026-10", Decimal("600"))])
        self.assertContains(response, 'aria-label="Solduri lunare economii"')
        SavingsMovement.objects.create(owner=self.user, occurred_on=date(2026, 10, 4), amount=Decimal("800"), kind="withdrawal")
        response = self.client.get("/dashboard/?month=2026-10")
        self.assertEqual(response.context["savings_evolution"][-1]["balance"], Decimal("-200"))
        self.assertContains(response, "De acoperit pentru revenirea la zero")
