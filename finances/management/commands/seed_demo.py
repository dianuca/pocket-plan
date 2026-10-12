from datetime import date
from decimal import Decimal
from getpass import getpass

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from dashboard.forms import MonthField
from finances.models import Expense, Income, Installment


class Command(BaseCommand):
    help = "Adaugă date fictive pentru contul demo, fără ștergeri sau suprascrieri."

    def add_arguments(self, parser):
        parser.add_argument("--month", default=date.today().strftime("%Y-%m"))

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            month = MonthField().clean(options["month"])
        except ValidationError as error:
            raise CommandError("Lună invalidă. Folosește YYYY-MM.") from error

        user, created = get_user_model().objects.get_or_create(username="pocketplan_demo")
        if created:
            password = getpass("Parola pentru noul cont pocketplan_demo: ")
            if not password:
                raise CommandError("Parola nu poate fi goală; nu s-au salvat date.")
            user.set_password(password)
            user.save(update_fields=["password"])

        year, month_number = map(int, month.split("-"))
        created_count = 0

        def add(model, **fields):
            nonlocal created_count
            _, was_created = model.objects.get_or_create(owner=user, **fields)
            created_count += int(was_created)

        add(Income, source="Demo: salariu", amount=Decimal("6500.00"),
            received_on=date(year, month_number, 5))
        add(Income, source="Demo: proiect freelance", amount=Decimal("850.00"),
            received_on=date(year, month_number, 12))

        for name, category, amount, day in [
            ("Chirie", Expense.Category.RENT, "1800.00", 1),
            ("Electricitate", Expense.Category.UTILITIES, "180.50", 8),
            ("Internet", Expense.Category.UTILITIES, "65.00", 9),
            ("Abonament muzică", Expense.Category.SUBSCRIPTIONS, "25.00", 10),
            ("Cumpărături", Expense.Category.FOOD, "320.75", 6),
            ("Piață", Expense.Category.FOOD, "145.25", 13),
            ("Transport public", Expense.Category.TRANSPORT, "80.00", 2),
            ("Cărți", Expense.Category.OTHER, "120.00", 15),
        ]:
            add(Expense, name=f"Demo: {name}", category=category,
                amount=Decimal(amount), paid_on=date(year, month_number, day))

        add(Installment, name=f"Demo: laptop ({month})",
            monthly_amount=Decimal("300.00"),
            first_due_on=date(year, month_number, 15), number_of_installments=3)

        self.stdout.write(self.style.SUCCESS(
            f"{created_count} înregistrări adăugate pentru pocketplan_demo, luna {month}. "
            "Datele și parola existente au fost păstrate."
        ))
