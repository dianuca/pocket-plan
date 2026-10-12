from datetime import date
from decimal import Decimal
from getpass import getpass

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from dashboard.forms import MonthField
from finances.models import Expense, Income, Installment, SavingsAccount, SavingsMovement


class Command(BaseCommand):
    help = "Adaugă date fictive pentru contul demo, fără ștergeri sau suprascrieri."

    def add_arguments(self, parser):
        parser.add_argument("--month", default=date.today().strftime("%Y-%m"))
        parser.add_argument("--savings", action="store_true", help="Include economii și transferuri demo în luna aleasă.")
        parser.add_argument("--months", type=int, default=1, help="Numărul de luni de economii, până la --month inclusiv (1–120).")

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            month = MonthField().clean(options["month"])
        except ValidationError as error:
            raise CommandError("Lună invalidă. Folosește YYYY-MM.") from error

        month_count = options["months"]
        if not 1 <= month_count <= 120:
            raise CommandError("--months trebuie să fie între 1 și 120.")
        if month_count != 1 and not options["savings"]:
            raise CommandError("Folosește --savings împreună cu --months.")
        year, month_number = map(int, month.split("-"))
        last_index = (year - 1) * 12 + month_number - 1
        first_index = last_index - month_count + 1
        if first_index < 0:
            raise CommandError("Intervalul de luni depășește începutul calendarului.")

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

        if options["savings"]:
            first_year, first_month = divmod(first_index, 12)
            account, account_created = SavingsAccount.objects.get_or_create(
                owner=user, defaults={"opening_balance": Decimal("300.00"),
                                      "started_on": date(first_year + 1, first_month + 1, 1)},
            )
            created_count += int(account_created)
            skipped = 0
            for month_index in range(first_index, last_index + 1):
                seed_year, seed_month = divmod(month_index, 12)
                for kind, amount, day, description in [
                    ("deposit", "500.00", 5, "Depunere lunară"),
                    ("withdrawal", "1000.00", 10, "Retragere pentru urgență"),
                    ("deposit", "100.00", 15, "Acoperire parțială deficit"),
                ]:
                    occurred_on = date(seed_year + 1, seed_month + 1, day)
                    if occurred_on < account.started_on:
                        skipped += 1
                        continue
                    add(SavingsMovement, kind=kind, amount=Decimal(amount),
                        occurred_on=occurred_on,
                        description=f"Demo: {description}")
            if skipped:
                self.stdout.write(self.style.WARNING(
                    f"{skipped} transferuri omise deoarece precedă data inițială existentă. "
                    "Soldul inițial și data lui nu au fost modificate."
                ))

        self.stdout.write(self.style.SUCCESS(
            f"{created_count} înregistrări adăugate pentru pocketplan_demo, luna {month}. "
            "Datele și parola existente au fost păstrate."
        ))
