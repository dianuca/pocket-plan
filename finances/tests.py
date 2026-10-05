from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from .models import Income
from .forms import IncomeForm
from .models import Expense, Income, Installment
from .forms import ExpenseForm, IncomeForm

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

class IncomeDeleteTests(TestCase):
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

    def test_get_displays_confirmation_without_deleting(self):
        response = self.client.get(
            f"/finances/incomes/{self.income.pk}/delete/",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "finances/income_confirm_delete.html",
        )
        self.assertTrue(
            Income.objects.filter(pk=self.income.pk).exists(),
        )

    def test_post_deletes_income(self):
        response = self.client.post(
            f"/finances/incomes/{self.income.pk}/delete/",
        )

        self.assertRedirects(
            response,
            "/finances/incomes/?month=2026-10",
        )
        self.assertFalse(
            Income.objects.filter(pk=self.income.pk).exists(),
        )

    def test_other_user_cannot_delete_income(self):
        other_user = get_user_model().objects.create_user(
            username="otheruser",
        )
        self.client.force_login(other_user)

        response = self.client.post(
            f"/finances/incomes/{self.income.pk}/delete/",
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(
            Income.objects.filter(pk=self.income.pk).exists(),
        )

class ExpenseModelTests(TestCase):
    def test_expense_is_saved_with_owner_and_category(self):
        user = get_user_model().objects.create_user(
            username="testuser",
        )

        expense = Expense.objects.create(
            owner=user,
            name="Netflix",
            category=Expense.Category.SUBSCRIPTIONS,
            amount=Decimal("50.00"),
            paid_on=date(2026, 10, 10),
        )

        saved_expense = Expense.objects.get(pk=expense.pk)

        self.assertEqual(saved_expense.owner, user)
        self.assertEqual(saved_expense.name, "Netflix")
        self.assertEqual(
            saved_expense.category,
            Expense.Category.SUBSCRIPTIONS,
        )
        self.assertEqual(saved_expense.amount, Decimal("50.00"))
        self.assertEqual(saved_expense.paid_on, date(2026, 10, 10))

class ExpenseFormTests(TestCase):
    def test_valid_expense_is_accepted(self):
        form = ExpenseForm(data={
            "name": "Netflix",
            "category": Expense.Category.SUBSCRIPTIONS,
            "amount": "50.00",
            "paid_on": "2026-10-10",
        })

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            form.cleaned_data["amount"],
            Decimal("50.00"),
        )

    def test_zero_and_negative_amounts_are_rejected(self):
        for amount in ["0.00", "-50.00"]:
            with self.subTest(amount=amount):
                form = ExpenseForm(data={
                    "name": "Netflix",
                    "category": Expense.Category.SUBSCRIPTIONS,
                    "amount": amount,
                    "paid_on": "2026-10-10",
                })

                self.assertFalse(form.is_valid())
                self.assertIn("amount", form.errors)

    def test_owner_is_not_editable(self):
        self.assertNotIn("owner", ExpenseForm().fields)

class ExpensePageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="testuser",
        )
        self.client.force_login(self.user)

    def test_submission_saves_expense_for_logged_in_user(self):
        response = self.client.post(
            "/finances/expenses/",
            data={
                "name": "Netflix",
                "category": Expense.Category.SUBSCRIPTIONS,
                "amount": "50.00",
                "paid_on": "2026-10-10",
            },
        )

        self.assertRedirects(
            response,
            "/finances/expenses/?month=2026-10",
        )

        expense = Expense.objects.get()

        self.assertEqual(expense.owner, self.user)
        self.assertEqual(expense.name, "Netflix")
        self.assertEqual(expense.amount, Decimal("50.00"))
        self.assertEqual(
            expense.category,
            Expense.Category.SUBSCRIPTIONS,
        )
        self.assertEqual(expense.paid_on, date(2026, 10, 10))

    def test_list_shows_only_current_user_and_selected_month(self):
        other_user = get_user_model().objects.create_user(
            username="otheruser",
        )

        for owner, name, paid_on in [
            (self.user, "Netflix octombrie", date(2026, 10, 10)),
            (self.user, "Netflix septembrie", date(2026, 9, 10)),
            (other_user, "Cheltuială alt utilizator", date(2026, 10, 10)),
        ]:
            Expense.objects.create(
                owner=owner,
                name=name,
                category=Expense.Category.SUBSCRIPTIONS,
                amount=Decimal("50.00"),
                paid_on=paid_on,
            )

        response = self.client.get(
            "/finances/expenses/",
            {"month": "2026-10"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Netflix octombrie")
        self.assertNotContains(response, "Netflix septembrie")
        self.assertNotContains(response, "Cheltuială alt utilizator")

    def test_anonymous_user_is_redirected_to_login(self):
        self.client.logout()

        response = self.client.get("/finances/expenses/")

        self.assertRedirects(
            response,
            "/accounts/login/?next=/finances/expenses/",
        )

class ExpenseEditTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="testuser",
        )
        self.client.force_login(self.user)

        self.expense = Expense.objects.create(
            owner=self.user,
            name="Netflix",
            category=Expense.Category.SUBSCRIPTIONS,
            amount=Decimal("50.00"),
            paid_on=date(2026, 10, 10),
        )

    def test_owner_can_edit_expense(self):
        response = self.client.post(
            f"/finances/expenses/{self.expense.pk}/edit/",
            data={
                "name": "Netflix corectat",
                "category": Expense.Category.SUBSCRIPTIONS,
                "amount": "60.00",
                "paid_on": "2026-11-10",
            },
        )

        self.assertRedirects(
            response,
            "/finances/expenses/?month=2026-11",
        )

        self.expense.refresh_from_db()

        self.assertEqual(self.expense.name, "Netflix corectat")
        self.assertEqual(self.expense.amount, Decimal("60.00"))
        self.assertEqual(self.expense.paid_on, date(2026, 11, 10))
        self.assertEqual(self.expense.owner, self.user)

    def test_other_user_cannot_edit_expense(self):
        other_user = get_user_model().objects.create_user(
            username="otheruser",
        )
        self.client.force_login(other_user)

        url = f"/finances/expenses/{self.expense.pk}/edit/"

        for method in ["get", "post"]:
            with self.subTest(method=method):
                response = getattr(self.client, method)(url)
                self.assertEqual(response.status_code, 404)

        self.expense.refresh_from_db()
        self.assertEqual(self.expense.amount, Decimal("50.00"))

class ExpenseDeleteTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="testuser",
        )
        self.client.force_login(self.user)

        self.expense = Expense.objects.create(
            owner=self.user,
            name="Netflix",
            category=Expense.Category.SUBSCRIPTIONS,
            amount=Decimal("50.00"),
            paid_on=date(2026, 10, 10),
        )

    def test_get_displays_confirmation_without_deleting(self):
        response = self.client.get(
            f"/finances/expenses/{self.expense.pk}/delete/",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "finances/expense_confirm_delete.html",
        )
        self.assertTrue(
            Expense.objects.filter(pk=self.expense.pk).exists(),
        )

    def test_post_deletes_expense(self):
        response = self.client.post(
            f"/finances/expenses/{self.expense.pk}/delete/",
        )

        self.assertRedirects(
            response,
            "/finances/expenses/?month=2026-10",
        )
        self.assertFalse(
            Expense.objects.filter(pk=self.expense.pk).exists(),
        )

    def test_other_user_cannot_access_or_delete_expense(self):
        other_user = get_user_model().objects.create_user(
            username="otheruser",
        )
        self.client.force_login(other_user)

        url = f"/finances/expenses/{self.expense.pk}/delete/"

        for method in ["get", "post"]:
            with self.subTest(method=method):
                response = getattr(self.client, method)(url)
                self.assertEqual(response.status_code, 404)

        self.assertTrue(
            Expense.objects.filter(pk=self.expense.pk).exists(),
        )

class InstallmentModelTests(TestCase):
    def test_installment_is_saved_with_owner_and_schedule(self):
        user = get_user_model().objects.create_user(
            username="testuser",
        )

        installment = Installment.objects.create(
            owner=user,
            name="Laptop",
            monthly_amount=Decimal("200.00"),
            first_due_on=date(2026, 10, 15),
            number_of_installments=3,
        )

        saved = Installment.objects.get(pk=installment.pk)

        self.assertEqual(saved.owner, user)
        self.assertEqual(saved.name, "Laptop")
        self.assertEqual(saved.monthly_amount, Decimal("200.00"))
        self.assertEqual(saved.first_due_on, date(2026, 10, 15))
        self.assertEqual(saved.number_of_installments, 3)

