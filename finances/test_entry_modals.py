from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Expense, Income, Installment


class EntryModalTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="owner")
        self.client.force_login(user)

    def test_creation_pages_render_modal_and_preserve_invalid_submission(self):
        for resource, field, model in [
            ("incomes", "source", Income), ("expenses", "name", Expense),
            ("installments", "name", Installment),
        ]:
            with self.subTest(resource=resource):
                url = f"/finances/{resource}/?month=2026-10"
                response = self.client.get(url)
                self.assertContains(response, '<dialog id="entry-panel"')
                self.assertContains(response, 'data-has-errors="false"')
                self.assertContains(response, "data-close-entry")
                response = self.client.post(url, {field: "De păstrat"})
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'data-has-errors="true"')
                self.assertContains(response, 'value="De păstrat"')
                self.assertTrue(response.context["form"].errors)
                self.assertFalse(model.objects.exists())
