from django.test import SimpleTestCase
from decimal import Decimal
from .services import calculate_expenses 


class DashboardPageTests(SimpleTestCase):
    def test_dashboard_displays_monthly_summary(self):
        response = self.client.get("/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "dashboard/summary.html",
        )
        self.assertContains(response, "Rezumat lunar")
        self.assertIn("income", response.context)
        self.assertIn("expenses", response.context)
        self.assertIn("balance", response.context)

    def test_balance_equals_income_minus_expenses(self):
        response = self.client.get("/dashboard/")
        context = response.context

        self.assertIsInstance(context["income"], Decimal)
        self.assertIsInstance(context["expenses"], Decimal)
        self.assertEqual(
            context["balance"],
            context["income"] - context["expenses"],
        )

    def test_dashboard_uses_selected_month(self):
        response = self.client.get(
            "/dashboard/",
            {"month": "2026-10"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["selected_month"],
            "2026-10",
        )
        self.assertContains(response, 'type="month"')
        self.assertContains(response, 'value="2026-10"')

    def test_dashboard_rejects_invalid_month(self):
        response = self.client.get(
            "/dashboard/",
            {"month": "2026-13"},
        )

        self.assertEqual(response.status_code, 400)

    def test_dashboard_displays_expense_list(self):
        response = self.client.get("/dashboard/")

        self.assertIn("expense_items", response.context)
        self.assertContains(response, "Chirie")
        self.assertContains(response, "Utilități")
        self.assertContains(response, "Abonamente")

class FinancialCalculationTests(SimpleTestCase):
    def test_calculates_expense_total(self):
        items = [
            {"name": "Chirie", "amount": Decimal("2500.00")},
            {"name": "Utilități", "amount": Decimal("500.50")},
        ]

        total = calculate_expenses(items)

        self.assertEqual(total, Decimal("3000.50"))

    def test_empty_expenses_return_decimal_zero(self):
        total = calculate_expenses([])

        self.assertEqual(total, Decimal("0.00"))
        self.assertIsInstance(total, Decimal)