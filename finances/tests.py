from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from .models import Income
from .forms import IncomeForm


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

class IncomeFormTests(TestCase):
    def test_valid_income_data_is_accepted(self):
        form = IncomeForm(data={
            "source": "Salariu",
            "amount": "5000.00",
            "received_on": "2026-10-05",
        })

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            form.cleaned_data["amount"],
            Decimal("5000.00"),
        )

    def test_zero_and_negative_amounts_are_rejected(self):
        for amount in ["0.00", "-100.00"]:
            with self.subTest(amount=amount):
                form = IncomeForm(data={
                    "source": "Salariu",
                    "amount": amount,
                    "received_on": "2026-10-05",
                })

                self.assertFalse(form.is_valid())
                self.assertIn("amount", form.errors)

    def test_owner_is_not_an_editable_field(self):
        form = IncomeForm()

        self.assertNotIn("owner", form.fields)

class IncomePageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="testuser",
            password="TestPassword123!",
        )
        self.client.force_login(self.user)

    def test_submission_saves_income_for_logged_in_user(self):
        response = self.client.post(
            "/finances/incomes/",
            data={
                "source": "Salariu",
                "amount": "5000.00",
                "received_on": "2026-10-05",
            },
        )

        self.assertRedirects(
            response,
            "/finances/incomes/?month=2026-10",
        )

        income = Income.objects.get()

        self.assertEqual(income.owner, self.user)
        self.assertEqual(income.source, "Salariu")
        self.assertEqual(income.amount, Decimal("5000.00"))
        self.assertEqual(income.received_on, date(2026, 10, 5))

    def test_anonymous_user_cannot_access_income_page(self):
        self.client.logout()

        response = self.client.get("/finances/incomes/")

        self.assertRedirects(
            response,
            "/accounts/login/?next=/finances/incomes/",
        )

    def test_list_shows_only_current_user_and_selected_month(self):
        other_user = get_user_model().objects.create_user(
            username="otheruser",
        )

        Income.objects.create(
            owner=self.user,
            source="Salariu octombrie",
            amount=Decimal("5000.00"),
            received_on=date(2026, 10, 5),
        )
        Income.objects.create(
            owner=self.user,
            source="Venit septembrie",
            amount=Decimal("900.00"),
            received_on=date(2026, 9, 5),
        )
        Income.objects.create(
            owner=other_user,
            source="Venit alt utilizator",
            amount=Decimal("7000.00"),
            received_on=date(2026, 10, 5),
        )

        response = self.client.get(
            "/finances/incomes/",
            {"month": "2026-10"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Salariu octombrie")
        self.assertNotContains(response, "Venit septembrie")
        self.assertNotContains(response, "Venit alt utilizator")

class IncomeEditTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="testuser",
        )
        self.client.force_login(self.user)

        self.income = Income.objects.create(
            owner=self.user,
            source="Salariu",
            amount=Decimal("5000.00"),
            received_on=date(2026, 10, 5),
        )

    def test_owner_can_edit_income(self):
        response = self.client.post(
            f"/finances/incomes/{self.income.pk}/edit/",
            data={
                "source": "Salariu corectat",
                "amount": "5200.00",
                "received_on": "2026-10-06",
            },
        )

        self.assertRedirects(
            response,
            "/finances/incomes/?month=2026-10",
        )

        self.income.refresh_from_db()

        self.assertEqual(self.income.source, "Salariu corectat")
        self.assertEqual(self.income.amount, Decimal("5200.00"))
        self.assertEqual(self.income.received_on, date(2026, 10, 6))
        self.assertEqual(self.income.owner, self.user)

    def test_other_user_cannot_edit_income(self):
        other_user = get_user_model().objects.create_user(
            username="otheruser",
        )
        self.client.force_login(other_user)

        url = f"/finances/incomes/{self.income.pk}/edit/"

        for method in ["get", "post"]:
            with self.subTest(method=method):
                response = getattr(self.client, method)(url)

                self.assertEqual(response.status_code, 404)

        self.income.refresh_from_db()
        self.assertEqual(self.income.amount, Decimal("5000.00"))
