from datetime import date
from decimal import Decimal
from io import BytesIO

from pypdf import PdfReader

from django.contrib.auth import get_user_model
from django.test import TestCase

from finances.models import Expense, Income, Installment, PersonalBudget, SavingsAccount, SavingsMovement


class MonthlyReportTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="owner")
        self.other = get_user_model().objects.create_user(username="other")
        self.client.force_login(self.user)

    def test_personal_budget_totals_match_summary_and_pdf_without_double_counting(self):
        Income.objects.create(owner=self.user, source="Salariu", amount=Decimal("5000"), received_on=date(2026, 10, 1))
        Expense.objects.create(owner=self.user, name="Chirie", category="rent", amount=Decimal("1000"), paid_on=date(2026, 10, 2))
        personal = Expense.objects.create(owner=self.user, name="Carte personală", category="other", amount=Decimal("200"), paid_on=date(2026, 10, 3), from_personal_budget=True)
        Installment.objects.create(owner=self.user, name="Laptop", monthly_amount=Decimal("300"), first_due_on=date(2026, 10, 1), number_of_installments=3)
        SavingsAccount.objects.create(owner=self.user, opening_balance=Decimal("0"), started_on=date(2026, 10, 1))
        for kind, amount in [("deposit", "400"), ("withdrawal", "100")]:
            SavingsMovement.objects.create(owner=self.user, kind=kind, amount=Decimal(amount), occurred_on=date(2026, 10, 2))
        allocation = PersonalBudget.objects.create(owner=self.user, month=date(2026, 10, 1), amount=Decimal("500"))
        PersonalBudget.objects.create(owner=self.other, month=date(2026, 10, 1), amount=Decimal("9999"))
        PersonalBudget.objects.create(owner=self.user, month=date(2026, 9, 1), amount=Decimal("8888"))
        for allocated, remaining, available in [("500", "300", "2900"), ("100", "-100", "3200"), ("0", "-200", "3200")]:
            with self.subTest(allocated=allocated):
                allocation.amount = Decimal(allocated)
                allocation.save()
                report = self.client.get("/dashboard/report/?month=2026-10")
                summary = self.client.get("/dashboard/?month=2026-10")
                for key in ["personal_allocated", "personal_spent", "personal_remaining", "personal_reserved", "personal_overspent", "unallocated_balance", "balance", "expenses"]:
                    self.assertEqual(report.context[key], summary.context[key])
                self.assertEqual(report.context["personal_remaining"], Decimal(remaining))
                self.assertEqual(report.context["unallocated_balance"], Decimal(available))
                self.assertEqual(report.context["expenses"], Decimal("1500"))
                self.assertEqual(report.context["balance"], Decimal("3200"))
                text = self.pdf_text(self.client.get("/dashboard/report/pdf/?month=2026-10"))
                self.assertIn("Buget pentru mine", text)
                self.assertIn("Carte personală (Pentru mine)", text)
                self.assertRegex(text, rf"Bani disponibili\s+{Decimal(available):.2f}".replace(".", ",") + " lei")
                self.assertRegex(text, rf"Rămas din alocare\s+{Decimal(remaining):.2f}".replace(".", ",") + " lei")
                self.assertNotIn("9999,00", text)
                self.assertNotIn("8888,00", text)
        self.assertEqual(PersonalBudget.objects.count(), 3)
        self.assertEqual(Expense.objects.count(), 2)
        # Raportul este dinamic: după editarea cheltuielii folosește datele noi.
        personal.amount = Decimal("250")
        personal.save()
        report = self.client.get("/dashboard/report/?month=2026-10")
        self.assertEqual(report.context["personal_spent"], Decimal("250"))
        self.assertEqual(report.context["unallocated_balance"], Decimal("3150"))
        text = self.pdf_text(self.client.get("/dashboard/report/pdf/?month=2026-10"))
        self.assertRegex(text, r"Bani disponibili\s+3150,00 lei")

    def test_report_matches_summary_and_scopes_all_details(self):
        for owner, month in [(self.user, 10), (self.other, 10), (self.user, 9)]:
            suffix = f"{owner.username}-{month}"
            Income.objects.create(owner=owner, source=f"Salaire-{suffix}", amount=Decimal("5000.00"), received_on=date(2026, month, 1))
            Expense.objects.create(owner=owner, name=f"Chirie-{suffix}", category="rent", amount=Decimal("2000.00"), paid_on=date(2026, month, 2))
            SavingsMovement.objects.create(owner=owner, kind="deposit", amount=Decimal("500.00"), occurred_on=date(2026, month, 3), description=f"Transfer-{suffix}")
        SavingsAccount.objects.create(owner=self.user, opening_balance=Decimal("100.00"), started_on=date(2026, 9, 1))
        SavingsMovement.objects.create(owner=self.user, kind="withdrawal", amount=Decimal("200.00"), occurred_on=date(2026, 10, 4))
        for owner, name, first_date in [
            (self.user, "Laptop", date(2026, 10, 1)),
            (self.other, "Rată străină", date(2026, 10, 1)),
            (self.user, "Rată expirată", date(2026, 6, 1)),
            (self.user, "Rată viitoare", date(2026, 11, 1)),
        ]:
            Installment.objects.create(owner=owner, name=name, monthly_amount=Decimal("300.00"), first_due_on=first_date, number_of_installments=3)
        response = self.client.get("/dashboard/report/?month=2026-10")
        self.assertEqual(response.status_code, 200)
        summary = self.client.get("/dashboard/?month=2026-10")
        for key in ["income", "expenses", "balance", "installment_total", "savings_balance", "savings_deposits", "savings_withdrawals"]:
            self.assertEqual(response.context[key], summary.context[key])
        self.assertEqual(response.context["balance"], Decimal("2400.00"))
        self.assertEqual(response.context["direct_expenses"], Decimal("2000.00"))
        self.assertEqual(response.context["savings_balance"], Decimal("900.00"))
        for text in ["Salaire-owner-10", "Chirie-owner-10", "Transfer-owner-10", "Laptop"]:
            self.assertContains(response, text)
        for text in ["Salaire-other-10", "Chirie-other-10", "Transfer-other-10", "Salaire-owner-9", "Chirie-owner-9", "Transfer-owner-9", "Rată străină", "Rată expirată", "Rată viitoare"]:
            self.assertNotContains(response, text)

    def test_empty_month_and_invalid_month(self):
        response = self.client.get("/dashboard/report/?month=2026-10")
        self.assertEqual(response.context["balance"], Decimal("0.00"))
        for text in ["Nu există venituri", "Nu există cheltuieli", "Nu există rate active", "Nu există transferuri"]:
            self.assertContains(response, text)
        for month in ["2026-13", "invalid", "0000-01", ""]:
            self.assertEqual(self.client.get("/dashboard/report/", {"month": month}).status_code, 400)

    def test_report_is_live_read_only_and_requires_login(self):
        income = Income.objects.create(owner=self.user, source="<script>demo</script>", amount=Decimal("100.00"), received_on=date(2026, 10, 1))
        response = self.client.get("/dashboard/report/?month=2026-10")
        self.assertContains(response, "&lt;script&gt;demo&lt;/script&gt;")
        self.assertEqual(Income.objects.count(), 1)
        income.amount = Decimal("200.00")
        income.save()
        self.assertEqual(self.client.get("/dashboard/report/?month=2026-10").context["income"], Decimal("200.00"))
        self.client.logout()
        self.assertEqual(self.client.get("/dashboard/report/").status_code, 302)

    def pdf_text(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF-"))
        return "\n".join(page.extract_text() for page in PdfReader(BytesIO(response.content)).pages)

    def test_pdf_content_scoping_diacritics_and_live_totals(self):
        self.test_report_matches_summary_and_scopes_all_details()
        Income.objects.create(owner=self.user, source="Știință & <b>învățare</b>", amount=Decimal("123.45"), received_on=date(2026, 10, 5))
        response = self.client.get("/dashboard/report/pdf/?month=2026-10")
        text = self.pdf_text(response)
        self.assertEqual(response["Content-Disposition"], 'inline; filename="pocketplan-2026-10.pdf"')
        self.assertEqual(response["Cache-Control"], "private, no-store")
        for value in ["2026-10", "Știință & <b>învățare</b>", "2523,45 lei", "900,00 lei", "Laptop", "Transfer-owner-10"]:
            self.assertIn(value, text)
        for value in ["Salaire-other-10", "Chirie-other-10", "Transfer-other-10", "Salaire-owner-9", "Chirie-owner-9", "Transfer-owner-9", "Rată străină", "Rată viitoare", "Rată expirată"]:
            self.assertNotIn(value, text)
        self.assertEqual(Income.objects.count(), 4)
        summary = self.client.get("/dashboard/?month=2026-10")
        self.assertContains(summary, '/dashboard/report/pdf/?month=2026-10')
        self.assertContains(summary, 'target="_blank"')

    def test_pdf_empty_invalid_and_unauthenticated(self):
        text = self.pdf_text(self.client.get("/dashboard/report/pdf/?month=2026-10"))
        for value in ["Nu există venituri", "Nu există cheltuieli", "Nu există rate active", "Nu există transferuri", "0,00 lei"]:
            self.assertIn(value, text)
        for month in ["", "2026-13", "invalid", "0000-01"]:
            self.assertEqual(self.client.get("/dashboard/report/pdf/", {"month": month}).status_code, 400)
        self.client.logout()
        self.assertEqual(self.client.get("/dashboard/report/pdf/").status_code, 302)

    def test_pdf_long_table_pagination_and_repeated_headers(self):
        Expense.objects.bulk_create([
            Expense(owner=self.user, name=f"Cheltuială {index:03d} " + "detalii " * 9,
                    category="food", amount=Decimal("10.00"), paid_on=date(2026, 10, 2))
            for index in range(100)
        ])
        response = self.client.get("/dashboard/report/pdf/?month=2026-10")
        text = self.pdf_text(response)
        pages = PdfReader(BytesIO(response.content)).pages
        self.assertGreater(len(pages), 2)
        self.assertIn("Cheltuială 000", text)
        self.assertIn("Cheltuială 099", text)
        self.assertIn("-1000,00 lei", text)
        for number, page in enumerate(pages, 1):
            page_text = page.extract_text()
            self.assertIn(f"Pagina {number}", page_text)
            if "Cheltuială" in page_text:
                self.assertIn("Categorie", page_text)
