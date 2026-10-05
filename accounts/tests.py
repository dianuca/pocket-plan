from django.test import SimpleTestCase
from accounts.forms import LoginForm
from django.contrib.auth import get_user_model
from django.test import TestCase

class LoginPageTests(SimpleTestCase):
    def test_login_page_is_accessible(self):
        response = self.client.get("/accounts/login/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/login.html")
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')
        self.assertTemplateUsed(response, "base.html")

    def test_home_redirects_to_login(self):
        response = self.client.get("/")
        self.assertRedirects(
            response,
            "/accounts/login/",
            status_code=302,
        )
        
    def test_empty_submission_shows_errors(self):
        response = self.client.post(
            "/accounts/login/",
            data={"username": "", "password": ""},
        )

        self.assertEqual(response.status_code, 200)

        form = response.context["form"]

        self.assertTrue(form.is_bound)
        self.assertIn("username", form.errors)
        self.assertIn("password", form.errors)

class LoginFormTests(SimpleTestCase):
    def test_empty_fields_are_invalid(self):
        form = LoginForm(data={
            "username": "",
            "password": "",
        })

        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)
        self.assertIn("password", form.errors)

    def test_filled_fields_are_valid(self):
        form = LoginForm(data={
            "username": "diana",
            "password": "example-password",
        })

        self.assertTrue(form.is_valid())

class LoginAuthenticationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="testuser",
            password="TestPassword123!",
        )

    def test_valid_credentials_log_user_in(self):
        response = self.client.post(
            "/accounts/login/",
            data={
                "username": "testuser",
                "password": "TestPassword123!",
            },
        )

        self.assertRedirects(response, "/dashboard/")
        self.assertEqual(
            int(self.client.session["_auth_user_id"]),
            self.user.pk,
        )

    def test_wrong_password_does_not_log_user_in(self):
        response = self.client.post(
            "/accounts/login/",
            data={
                "username": "testuser",
                "password": "wrong-password",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(
            response,
            "Utilizator sau parolă incorectă.",
        )