from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Expense, Income, SavingsAccount, SavingsMovement
from .savings import savings_evolution, savings_summary


class SavingsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="owner")
        self.other = get_user_model().objects.create_user(username="other")
        self.client.force_login(self.user)
        self.account = SavingsAccount.objects.create(
            owner=self.user, opening_balance=Decimal("100.00"), started_on=date(2026, 9, 1),
        )

    def movement(self, kind, amount, occurred_on, owner=None):
        return SavingsMovement.objects.create(
            owner=owner or self.user, kind=kind, amount=Decimal(amount), occurred_on=occurred_on,
        )

    def test_evolution_carries_prior_balance_and_excludes_other_user_and_future(self):
        self.movement("deposit", "200.00", date(2026, 9, 1))
        self.movement("withdrawal", "500.00", date(2027, 1, 1))
        self.movement("deposit", "800.00", date(2027, 11, 1))
        self.movement("deposit", "900.00", date(2027, 1, 1), owner=self.other)
        points = savings_evolution(self.user, "2027-10")
        self.assertEqual(len(points), 12)
        self.assertEqual(points[0], {"month": "2026-11", "balance": Decimal("300.00"), "height": 100})
        self.assertEqual(points[-1]["balance"], Decimal("-200.00"))
        self.assertEqual(points[-1]["height"], 66)
        self.assertEqual(points[-1]["balance"], savings_summary(self.user, "2027-10")["savings_balance"])

    def test_evolution_handles_before_start_and_zero_scale(self):
        self.assertEqual(savings_evolution(self.user, "2026-08"), [])
        self.assertEqual(savings_evolution(self.other, "2026-10"), [])
        self.account.opening_balance = Decimal("0.00")
        self.account.save()
        points = savings_evolution(self.user, "2026-10")
        self.assertEqual([point["height"] for point in points], [0, 0])
        response = self.client.get("/finances/savings/?month=2026-10")
        self.assertContains(response, "Evoluția economiilor")

    def test_deficit_message_disappears_when_savings_return_to_zero(self):
        self.movement("withdrawal", "150.00", date(2026, 10, 1))
        for url in ["/finances/savings/?month=2026-10", "/dashboard/?month=2026-10"]:
            response = self.client.get(url)
            self.assertEqual(response.context["savings_deficit"], Decimal("50.00"))
            self.assertContains(response, 'class="savings-deficit"')
            self.assertContains(response, 'class="savings-negative"')
            self.assertContains(response, "De acoperit: 50.00 lei")
        self.movement("deposit", "50.00", date(2026, 10, 2))
        for url in ["/finances/savings/?month=2026-10", "/dashboard/?month=2026-10"]:
            response = self.client.get(url)
            self.assertEqual(response.context["savings_balance"], Decimal("0.00"))
            self.assertNotContains(response, 'class="savings-deficit"')
            self.assertNotContains(response, 'class="savings-negative"')

    def test_history_filters_preserve_running_balance_and_owner_isolation(self):
        self.movement("deposit", "200.00", date(2026, 9, 1))
        withdrawal = self.movement("withdrawal", "400.00", date(2026, 10, 1))
        deposit = self.movement("deposit", "20.00", date(2026, 10, 1))
        self.movement("deposit", "900.00", date(2026, 11, 1))
        self.movement("deposit", "800.00", date(2026, 10, 1), owner=self.other)
        response = self.client.get("/finances/savings/history/", {
            "start": "2026-10-01", "end": "2026-10-31",
        })
        rows = list(response.context["page_obj"])
        self.assertEqual(rows, [
            {"movement": deposit, "balance": Decimal("-80.00")},
            {"movement": withdrawal, "balance": Decimal("-100.00")},
        ])
        response = self.client.get("/finances/savings/history/", {"kind": "deposit", "end": "2026-10-31"})
        self.assertEqual(list(response.context["page_obj"])[0]["balance"], Decimal("-80.00"))

    def test_history_invalid_filters_empty_state_and_login(self):
        for filters in [{"start": "invalid"}, {"kind": "invalid"},
                        {"start": "2026-11-01", "end": "2026-10-01"}]:
            response = self.client.get("/finances/savings/history/", filters)
            self.assertTrue(response.context["filter_form"].errors)
        response = self.client.get("/finances/savings/history/")
        self.assertContains(response, "Nu există transferuri pentru filtrele selectate.")
        self.client.logout()
        self.assertEqual(self.client.get("/finances/savings/history/").status_code, 302)

    def test_history_overlay_receives_partial_and_keeps_validation(self):
        response = self.client.get("/finances/savings/history/", HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertTemplateUsed(response, "finances/includes/savings_history_content.html")
        self.assertNotContains(response, "<!DOCTYPE html>")
        self.assertContains(response, "data-close-history")
        response = self.client.get("/finances/savings/history/", {"start": "invalid"},
                                   HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertTrue(response.context["filter_form"].errors)

    def test_history_pagination_keeps_filters_and_full_balance(self):
        for _ in range(26):
            self.movement("deposit", "1.00", date(2026, 10, 1))
        response = self.client.get("/finances/savings/history/", {"kind": "deposit"})
        self.assertEqual(len(response.context["page_obj"]), 25)
        self.assertContains(response, "?kind=deposit&amp;page=2")
        response = self.client.get("/finances/savings/history/", {"kind": "deposit", "page": "2"})
        self.assertEqual(len(response.context["page_obj"]), 1)
        self.assertEqual(list(response.context["page_obj"])[0]["balance"], Decimal("101.00"))

    def test_edit_opening_balance_recalculates_history_without_affecting_budget(self):
        self.movement("deposit", "200.00", date(2026, 10, 10))
        response = self.client.post("/finances/savings/initial/edit/", {
            "edit-opening-opening_balance": "-50.00",
            "edit-opening-started_on": "2026-08-01", "owner": self.other.pk,
        })
        self.assertRedirects(response, "/finances/savings/?month=2026-08")
        self.account.refresh_from_db()
        self.assertEqual(self.account.owner, self.user)
        self.assertEqual(self.account.opening_balance, Decimal("-50.00"))
        self.assertEqual(savings_summary(self.user, "2026-07")["savings_balance"], Decimal("0.00"))
        self.assertEqual(savings_summary(self.user, "2026-09")["savings_deficit"], Decimal("50.00"))
        self.assertEqual(savings_summary(self.user, "2026-10")["savings_balance"], Decimal("150.00"))
        self.assertEqual(self.client.get("/dashboard/?month=2026-10").context["balance"], Decimal("-200.00"))

    def test_opening_date_cannot_hide_existing_transfer(self):
        self.movement("deposit", "200.00", date(2026, 9, 10))
        response = self.client.post("/finances/savings/initial/edit/", {
            "edit-opening-opening_balance": "999.00", "edit-opening-started_on": "2026-09-11",
        })
        self.assertIn("started_on", response.context["form"].errors)
        self.assertContains(response, 'value="999.00"')
        self.account.refresh_from_db()
        self.assertEqual(self.account.opening_balance, Decimal("100.00"))
        self.assertEqual(self.account.started_on, date(2026, 9, 1))
        response = self.client.post("/finances/savings/initial/edit/", {
            "edit-opening-opening_balance": "100.00", "edit-opening-started_on": "2026-09-10",
        })
        self.assertEqual(response.status_code, 302)

    def test_opening_edit_access_partial_and_no_mutation_on_get(self):
        url = "/finances/savings/initial/edit/"
        response = self.client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertTemplateUsed(response, "finances/includes/savings_action_form.html")
        self.assertContains(response, "Corectează soldul inițial")
        self.account.refresh_from_db()
        self.assertEqual(self.account.opening_balance, Decimal("100.00"))
        self.client.force_login(self.other)
        for method in ["get", "post"]:
            self.assertEqual(getattr(self.client, method)(url).status_code, 404)
        self.client.logout()
        for method in ["get", "post"]:
            self.assertEqual(getattr(self.client, method)(url).status_code, 302)

    def test_edit_moves_transfer_between_months_and_recalculates_balances(self):
        movement = self.movement("deposit", "200.00", date(2026, 9, 10))
        response = self.client.post(f"/finances/savings/{movement.pk}/edit/", {
            "edit-movement-kind": "withdrawal", "edit-movement-amount": "300.00",
            "edit-movement-occurred_on": "2026-10-10", "edit-movement-description": "Corectat",
            "owner": self.other.pk,
        })
        self.assertRedirects(response, "/finances/savings/?month=2026-10")
        movement.refresh_from_db()
        self.assertEqual(movement.owner, self.user)
        self.assertEqual(movement.description, "Corectat")
        self.assertEqual(savings_summary(self.user, "2026-09")["savings_balance"], Decimal("100.00"))
        self.assertEqual(savings_summary(self.user, "2026-10")["savings_balance"], Decimal("-200.00"))
        self.assertEqual(self.client.get("/dashboard/?month=2026-09").context["balance"], Decimal("0.00"))
        self.assertEqual(self.client.get("/dashboard/?month=2026-10").context["balance"], Decimal("300.00"))

    def test_invalid_edit_keeps_database_and_returns_errors_in_modal(self):
        movement = self.movement("deposit", "200.00", date(2026, 10, 10))
        response = self.client.post(f"/finances/savings/{movement.pk}/edit/", {
            "edit-movement-kind": "deposit", "edit-movement-amount": "-10.00",
            "edit-movement-occurred_on": "2026-08-01",
        })
        self.assertContains(response, 'id="savings-action-modal"')
        self.assertIn("amount", response.context["form"].errors)
        self.assertIn("occurred_on", response.context["form"].errors)
        self.assertContains(response, 'value="-10.00"')
        movement.refresh_from_db()
        self.assertEqual(movement.amount, Decimal("200.00"))
        self.assertEqual(movement.occurred_on, date(2026, 10, 10))

    def test_delete_requires_confirmation_and_handles_last_transfer(self):
        movement = self.movement("withdrawal", "200.00", date(2026, 10, 10))
        url = f"/finances/savings/{movement.pk}/delete/"
        response = self.client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertContains(response, "Confirmă ștergerea")
        self.assertTemplateUsed(response, "finances/includes/savings_action_form.html")
        self.assertTrue(SavingsMovement.objects.filter(pk=movement.pk).exists())
        self.assertRedirects(self.client.post(url), "/finances/savings/?month=2026-10")
        self.assertFalse(SavingsMovement.objects.exists())
        summary = savings_summary(self.user, "2026-10")
        self.assertEqual(summary["savings_balance"], Decimal("100.00"))
        self.assertEqual(summary["savings_deficit"], Decimal("0.00"))
        self.assertEqual(self.client.get("/dashboard/?month=2026-10").context["balance"], Decimal("0.00"))
        self.assertContains(self.client.get("/finances/savings/?month=2026-10"), "Nu există transferuri")

    def test_actions_reject_other_user_and_anonymous_requests(self):
        movement = self.movement("deposit", "200.00", date(2026, 10, 10))
        for action in ["edit", "delete"]:
            url = f"/finances/savings/{movement.pk}/{action}/"
            self.client.force_login(self.other)
            for method in ["get", "post"]:
                self.assertEqual(getattr(self.client, method)(url).status_code, 404)
            self.client.logout()
            for method in ["get", "post"]:
                self.assertEqual(getattr(self.client, method)(url).status_code, 302)
        self.assertTrue(SavingsMovement.objects.filter(pk=movement.pk).exists())

    def test_historical_balance_monthly_transfers_and_owner_isolation(self):
        self.movement("deposit", "200.00", date(2026, 9, 10))
        self.movement("withdrawal", "500.00", date(2026, 10, 2))
        self.movement("deposit", "900.00", date(2026, 11, 2))
        self.movement("deposit", "700.00", date(2026, 10, 2), owner=self.other)
        self.assertEqual(savings_summary(self.user, "2026-08")["savings_balance"], Decimal("0.00"))
        self.assertEqual(savings_summary(self.user, "2026-09")["savings_balance"], Decimal("300.00"))
        summary = savings_summary(self.user, "2026-10")
        self.assertEqual(summary, {
            "savings_balance": Decimal("-200.00"), "savings_deficit": Decimal("200.00"),
            "savings_deposits": Decimal("0.00"), "savings_withdrawals": Decimal("500.00"),
        })

    def test_transfers_adjust_available_without_changing_income_or_expenses(self):
        Income.objects.create(owner=self.user, source="Salariu", amount=Decimal("5000.00"), received_on=date(2026, 10, 1))
        Expense.objects.create(owner=self.user, name="Chirie", category="rent", amount=Decimal("3000.00"), paid_on=date(2026, 10, 1))
        self.movement("deposit", "500.00", date(2026, 10, 3))
        response = self.client.get("/dashboard/?month=2026-10")
        self.assertEqual(response.context["income"], Decimal("5000.00"))
        self.assertEqual(response.context["expenses"], Decimal("3000.00"))
        self.assertEqual(response.context["balance"], Decimal("1500.00"))
        self.movement("withdrawal", "800.00", date(2026, 10, 4))
        response = self.client.get("/dashboard/?month=2026-10")
        self.assertEqual(response.context["balance"], Decimal("2300.00"))
        self.assertEqual(response.context["savings_deficit"], Decimal("200.00"))

    def test_post_accepts_overdraft_and_ignores_submitted_owner(self):
        response = self.client.post("/finances/savings/?month=2026-10", {
            "movement-kind": "withdrawal", "movement-amount": "500.00",
            "movement-occurred_on": "2026-10-05", "movement-description": "Împrumut",
            "owner": self.other.pk,
        })
        self.assertRedirects(response, "/finances/savings/?month=2026-10")
        self.assertEqual(SavingsMovement.objects.get().owner, self.user)
        response = self.client.get("/finances/savings/?month=2026-10")
        self.assertEqual(response.context["savings_deficit"], Decimal("400.00"))
        self.assertContains(response, "De acoperit")

    def test_invalid_amount_date_and_kind_are_rejected(self):
        for field, value in [("amount", "0"), ("amount", "-1"), ("occurred_on", "2026-08-01"),
                             ("occurred_on", "invalid"), ("kind", "invalid")]:
            with self.subTest(field=field, value=value):
                data = {"movement-kind": "deposit", "movement-amount": "100.00",
                        "movement-occurred_on": "2026-10-01"}
                data[f"movement-{field}"] = value
                response = self.client.post("/finances/savings/", data)
                self.assertFormError(response.context["form"], field, response.context["form"].errors[field])
        self.assertFalse(SavingsMovement.objects.exists())

    def test_initial_setup_is_separate_from_monthly_transfers(self):
        self.client.force_login(self.other)
        response = self.client.post("/finances/savings/", {
            "opening-opening_balance": "-50.00", "opening-started_on": "2026-10-01",
            "owner": self.user.pk,
        })
        self.assertRedirects(response, "/finances/savings/?month=2026-10")
        self.assertEqual(SavingsAccount.objects.get(owner=self.other).opening_balance, Decimal("-50.00"))
        self.assertEqual(savings_summary(self.other, "2026-10")["savings_deposits"], Decimal("0.00"))
        self.assertEqual(SavingsAccount.objects.filter(owner=self.user).count(), 1)

    def test_list_filters_month_and_owner_and_escapes_description(self):
        movement = self.movement("deposit", "10.00", date(2026, 10, 1))
        movement.description = "<script>alert(1)</script>"
        movement.save()
        self.movement("deposit", "20.00", date(2026, 9, 1))
        self.movement("deposit", "30.00", date(2026, 10, 1), owner=self.other)
        response = self.client.get("/finances/savings/?month=2026-10")
        self.assertEqual(list(response.context["movements"]), [movement])
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, "<script>alert(1)</script>")

    def test_invalid_month_and_anonymous_access(self):
        self.assertEqual(self.client.get("/finances/savings/?month=2026-13").status_code, 400)
        self.client.logout()
        for method in ["get", "post"]:
            self.assertEqual(getattr(self.client, method)("/finances/savings/").status_code, 302)

    def test_modal_preserves_invalid_transfer_and_signals_reopening(self):
        response = self.client.post("/finances/savings/?month=2026-10", {
            "movement-kind": "withdrawal", "movement-amount": "-20.00",
            "movement-occurred_on": "2026-10-10", "movement-description": "De păstrat",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-has-errors="true"')
        self.assertContains(response, 'value="-20.00"')
        self.assertContains(response, 'value="De păstrat"')
        self.assertFalse(SavingsMovement.objects.exists())

    def test_initial_balance_modal_preserves_invalid_values(self):
        self.client.force_login(self.other)
        response = self.client.post("/finances/savings/", {
            "opening-opening_balance": "123.45", "opening-started_on": "invalid",
        })
        self.assertContains(response, "Configurează soldul inițial")
        self.assertContains(response, 'data-has-errors="true"')
        self.assertContains(response, 'value="123.45"')
        self.assertFalse(SavingsAccount.objects.filter(owner=self.other).exists())
