from django.test import SimpleTestCase
from decimal import Decimal


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