from django.test import SimpleTestCase
from decimal import Decimal
from .services import calculate_expenses 
from .services import installment_amount_for_month
from .services import remaining_installments
from .forms import InstallmentPreviewForm
from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date
from finances.models import Income
from finances.models import Expense, Income, Installment

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
        self.assertContains(response, "Luna selectată: 2026-10")
        self.assertTemplateUsed(response, "includes/month_picker.html")

    def test_dashboard_rejects_invalid_month(self):
        response = self.client.get(
            "/dashboard/",
            {"month": "2026-13"},
        )

        self.assertEqual(response.status_code, 400)

    def test_dashboard_displays_expense_list(self):
        owner = get_user_model().objects.get(username="testuser")

        Expense.objects.create(
            owner=owner,
            name="Netflix",
            category=Expense.Category.SUBSCRIPTIONS,
            amount=Decimal("50.00"),
            paid_on=date(2026, 10, 10),
        )

        response = self.client.get(
            "/dashboard/",
            {"month": "2026-10"},
        )

        self.assertContains(response, "Netflix")
        self.assertEqual(
            len(response.context["expense_items"]),
            1,
        )
   
    def test_dashboard_includes_active_installment(self):
        owner = get_user_model().objects.get(username="testuser")

        Installment.objects.create(
            owner=owner,
            name="Laptop",
            monthly_amount=Decimal("200.00"),
            first_due_on=date(2026, 10, 15),
            number_of_installments=3,
        )

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
            Decimal("200.00"),
        )
        self.assertContains(response, "Laptop")

    def test_dashboard_excludes_finished_installment(self):
        owner = get_user_model().objects.get(username="testuser")

        Installment.objects.create(
            owner=owner,
            name="Laptop",
            monthly_amount=Decimal("200.00"),
            first_due_on=date(2026, 10, 15),
            number_of_installments=3,
        )
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
            Decimal("0.00"),
        )

    def setUp(self):
        user = get_user_model().objects.create_user(
            username="testuser",
            password="TestPassword123!",
        )
        self.client.force_login(user)

    def test_income_total_uses_only_current_user_and_month(self):
        owner = get_user_model().objects.get(username="testuser")
        other_user = get_user_model().objects.create_user(
            username="otheruser",
        )

        Income.objects.create(
            owner=owner,
            source="Salariu",
            amount=Decimal("5000.00"),
            received_on=date(2026, 10, 5),
        )
        Income.objects.create(
            owner=owner,
            source="Proiect",
            amount=Decimal("500.00"),
            received_on=date(2026, 10, 10),
        )
        Income.objects.create(
            owner=owner,
            source="Venit din altă lună",
            amount=Decimal("900.00"),
            received_on=date(2026, 9, 5),
        )
        Income.objects.create(
            owner=other_user,
            source="Venitul altui utilizator",
            amount=Decimal("7000.00"),
            received_on=date(2026, 10, 5),
        )

        response = self.client.get(
            "/dashboard/",
            {"month": "2026-10"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["income"],
            Decimal("5500.00"),
        )

    def test_expenses_use_only_current_user_and_selected_month(self):
        owner = get_user_model().objects.get(username="testuser")
        other_user = get_user_model().objects.create_user(
            username="otheruser",
        )

        for user, name, amount, paid_on in [
            (owner, "Netflix octombrie", "50.00", date(2026, 10, 10)),
            (owner, "Internet octombrie", "100.00", date(2026, 10, 12)),
            (owner, "Cheltuială septembrie", "900.00", date(2026, 9, 5)),
            (other_user, "Cheltuială străină", "700.00", date(2026, 10, 5)),
        ]:
            Expense.objects.create(
                owner=user,
                name=name,
                category=Expense.Category.SUBSCRIPTIONS,
                amount=Decimal(amount),
                paid_on=paid_on,
            )

        response = self.client.get(
            "/dashboard/",
            {"month": "2026-10"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["expenses"],
            Decimal("150.00"),
        )
        self.assertContains(response, "Netflix octombrie")
        self.assertContains(response, "Internet octombrie")
        self.assertNotContains(response, "Cheltuială septembrie")
        self.assertNotContains(response, "Cheltuială străină")

    def test_installments_use_only_current_user_and_active_month(self):
        owner = get_user_model().objects.get(username="testuser")
        other_user = get_user_model().objects.create_user(
            username="otheruser",
        )

        for user, name, amount, first_due_on in [
            (owner, "Laptop personal", "200.00", date(2026, 10, 15)),
            (owner, "Telefon personal", "100.00", date(2026, 9, 10)),
            (owner, "Rată terminată", "500.00", date(2026, 6, 5)),
            (other_user, "Rată alt utilizator", "700.00", date(2026, 10, 5)),
        ]:
            Installment.objects.create(
                owner=user,
                name=name,
                monthly_amount=Decimal(amount),
                first_due_on=first_due_on,
                number_of_installments=3,
            )

        response = self.client.get(
            "/dashboard/",
            {"month": "2026-10"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["installment_total"],
            Decimal("300.00"),
        )
        self.assertEqual(
            response.context["expenses"],
            Decimal("300.00"),
        )
        self.assertContains(response, "Laptop personal")
        self.assertContains(response, "Telefon personal")
        self.assertNotContains(response, "Rată terminată")
        self.assertNotContains(response, "Rată alt utilizator")

class DashboardCategoryTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="owner")
        self.other = get_user_model().objects.create_user(username="other")
        self.client.force_login(self.owner)

    def test_chart_bars_share_scale_when_expenses_exceed_income(self):
        Income.objects.create(
            owner=self.owner, source="Salariu", amount=Decimal("100.00"),
            received_on=date(2026, 10, 1),
        )
        Expense.objects.create(
            owner=self.owner, name="Chirie", category=Expense.Category.RENT,
            amount=Decimal("200.00"), paid_on=date(2026, 10, 1),
        )

        response = self.client.get("/dashboard/", {"month": "2026-10"})

        self.assertEqual(response.context["comparison_max"], Decimal("200.00"))
        self.assertContains(response, 'chart-bar-income" style="width: 50%"')
        self.assertContains(response, 'chart-bar" style="width: 100%"', count=2)
        self.assertContains(response, "100% din cheltuieli")

    def test_income_only_month_shows_comparison_and_empty_distribution(self):
        Income.objects.create(
            owner=self.owner, source="Salariu", amount=Decimal("100.00"),
            received_on=date(2026, 10, 1),
        )

        response = self.client.get("/dashboard/", {"month": "2026-10"})

        self.assertEqual(response.context["comparison_max"], Decimal("100.00"))
        self.assertContains(response, 'chart-bar-income" style="width: 100%"')
        self.assertContains(response, 'chart-bar" style="width: 0%"')
        self.assertContains(response, "Nu există cheltuieli de reprezentat")

    def test_groups_categories_for_current_user_and_selected_month(self):
        for owner, category, amount, paid_on in [
            (self.owner, Expense.Category.FOOD, "20.10", date(2026, 10, 1)),
            (self.owner, Expense.Category.FOOD, "30.20", date(2026, 10, 2)),
            (self.owner, Expense.Category.RENT, "1000.00", date(2026, 10, 1)),
            (self.owner, Expense.Category.FOOD, "900.00", date(2026, 9, 1)),
            (self.other, Expense.Category.FOOD, "800.00", date(2026, 10, 1)),
            (self.other, Expense.Category.OTHER, "700.00", date(2026, 10, 1)),
        ]:
            Expense.objects.create(
                owner=owner, name="Cheltuială", category=category,
                amount=Decimal(amount), paid_on=paid_on,
            )

        response = self.client.get("/dashboard/", {"month": "2026-10"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["expenses_by_category"], [
            {"category": "food", "label": "Alimentație", "amount": Decimal("50.30")},
            {"category": "rent", "label": "Chirie", "amount": Decimal("1000.00")},
        ])
        self.assertEqual(response.context["expenses"], Decimal("1050.30"))

    def test_active_installments_form_separate_category_without_double_counting(self):
        Expense.objects.create(
            owner=self.owner, name="Mâncare", category=Expense.Category.FOOD,
            amount=Decimal("50.00"), paid_on=date(2026, 10, 1),
        )
        for owner, first_due_on, amount in [
            (self.owner, date(2026, 10, 15), "200.00"),
            (self.owner, date(2026, 9, 15), "100.00"),
            (self.owner, date(2026, 6, 15), "500.00"),
            (self.owner, date(2026, 11, 15), "600.00"),
            (self.other, date(2026, 10, 15), "700.00"),
        ]:
            Installment.objects.create(
                owner=owner, name="Rată", monthly_amount=Decimal(amount),
                first_due_on=first_due_on, number_of_installments=3,
            )

        response = self.client.get("/dashboard/", {"month": "2026-10"})
        rows = response.context["expenses_by_category"]

        self.assertEqual(rows, [
            {"category": "food", "label": "Alimentație", "amount": Decimal("50.00")},
            {"category": "installments", "label": "Rate", "amount": Decimal("300.00")},
        ])
        self.assertEqual(response.context["expenses"], Decimal("350.00"))
        self.assertEqual(
            sum((row["amount"] for row in rows), Decimal("0.00")),
            response.context["expenses"],
        )

    def test_month_without_expenses_or_active_installments_has_no_categories(self):
        Installment.objects.create(
            owner=self.owner, name="Rată terminată",
            monthly_amount=Decimal("200.00"),
            first_due_on=date(2026, 6, 15), number_of_installments=3,
        )

        response = self.client.get("/dashboard/", {"month": "2026-10"})

        self.assertEqual(response.context["expenses_by_category"], [])
        self.assertEqual(response.context["expenses"], Decimal("0.00"))
        self.assertContains(response, "Nu există cheltuieli de reprezentat")
        self.assertContains(response, "Nu există venituri sau cheltuieli în această lună.")
        self.assertNotContains(response, 'class="chart-track"')


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
