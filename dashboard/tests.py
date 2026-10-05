from django.test import SimpleTestCase
from decimal import Decimal
from .services import calculate_expenses 
from .services import installment_amount_for_month
from .services import remaining_installments
from .forms import InstallmentPreviewForm
from django.test import TestCase
from django.contrib.auth import get_user_model

class DashboardPageTests(TestCase):
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

    def test_dashboard_includes_active_installment(self):
        response = self.client.get(
            "/dashboard/",
            {"month": "2026-10"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["installment_total"],
            Decimal("200.00"),
        )
        self.assertEqual(
            response.context["expenses"],
            Decimal("3400.00"),
        )
        self.assertContains(response, "Laptop")

    def test_dashboard_excludes_finished_installment(self):
        response = self.client.get(
            "/dashboard/",
            {"month": "2027-01"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["installment_total"],
            Decimal("0.00"),
        )
        self.assertEqual(
            response.context["expenses"],
            Decimal("3200.00"),
        )

    def setUp(self):
        user = get_user_model().objects.create_user(
            username="testuser",
            password="TestPassword123!",
        )
        self.client.force_login(user)

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

class InstallmentCalculationTests(SimpleTestCase):
    def test_amount_applies_only_during_payment_months(self):
        cases = [
            ("2026-09", Decimal("0.00")),
            ("2026-10", Decimal("200.00")),
            ("2026-11", Decimal("200.00")),
            ("2026-12", Decimal("200.00")),
            ("2027-01", Decimal("0.00")),
        ]

        for month, expected in cases:
            with self.subTest(month=month):
                amount = installment_amount_for_month(
                    monthly_amount=Decimal("200.00"),
                    first_month="2026-10",
                    number_of_installments=3,
                    selected_month=month,
                )

                self.assertEqual(amount, expected)

    def test_installments_continue_into_next_year(self):
        cases = [
            ("2026-12", Decimal("200.00")),
            ("2027-01", Decimal("200.00")),
            ("2027-02", Decimal("200.00")),
            ("2027-03", Decimal("0.00")),
        ]

        for month, expected in cases:
            with self.subTest(month=month):
                amount = installment_amount_for_month(
                    monthly_amount=Decimal("200.00"),
                    first_month="2026-12",
                    number_of_installments=3,
                    selected_month=month,
                )

                self.assertEqual(amount, expected)

    def test_remaining_installments_include_selected_month(self):
        cases = [
            ("2026-09", 3),
            ("2026-10", 3),
            ("2026-11", 2),
            ("2026-12", 1),
            ("2027-01", 0),
            ("2027-06", 0),
        ]

        for month, expected in cases:
            with self.subTest(month=month):
                remaining = remaining_installments(
                    first_month="2026-10",
                    number_of_installments=3,
                    selected_month=month,
                )

                self.assertEqual(remaining, expected)

class InstallmentPreviewPageTests(TestCase):
    def test_preview_page_displays_form(self):
        response = self.client.get("/dashboard/installments/preview/")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "dashboard/installment_preview.html",
        )
        self.assertIsInstance(
            response.context["form"],
            InstallmentPreviewForm,
        )

    def test_valid_submission_calculates_preview(self):
        response = self.client.post(
            "/dashboard/installments/preview/",
            data={
                "name": "Laptop",
                "monthly_amount": "200.00",
                "first_month": "2026-10",
                "number_of_installments": "3",
                "selected_month": "2026-11",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["preview"]["amount"],
            Decimal("200.00"),
        )
        self.assertEqual(
            response.context["preview"]["remaining"],
            2,
        )
        self.assertContains(response, "Laptop")

    def setUp(self):
        user = get_user_model().objects.create_user(
            username="testuser",
            password="TestPassword123!",
        )
        self.client.force_login(user)

class ProtectedPageTests(TestCase):
    def test_anonymous_user_is_redirected_to_login(self):
        pages = [
            "/dashboard/",
            "/dashboard/installments/preview/",
        ]

        for page in pages:
            with self.subTest(page=page):
                response = self.client.get(page)

                self.assertRedirects(
                    response,
                    f"/accounts/login/?next={page}",
                )

class InstallmentPreviewFormTests(SimpleTestCase):
    def test_valid_installment_data_is_accepted(self):
        form = InstallmentPreviewForm(data={
            "name": "Laptop",
            "monthly_amount": "200.00",
            "first_month": "2026-10",
            "number_of_installments": "3",
            "selected_month": "2026-11",
        })

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            form.cleaned_data["monthly_amount"],
            Decimal("200.00"),
        )
        self.assertEqual(
            form.cleaned_data["number_of_installments"],
            3,
        )

    def test_zero_installments_are_rejected(self):
        form = InstallmentPreviewForm(data={
            "name": "Laptop",
            "monthly_amount": "200.00",
            "first_month": "2026-10",
            "number_of_installments": "0",
            "selected_month": "2026-11",
        })

        self.assertFalse(form.is_valid())
        self.assertIn("number_of_installments", form.errors)