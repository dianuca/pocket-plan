from django.conf import settings
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from decimal import Decimal


class BudgetPreference(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    start_day = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(31)])

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(start_day__gte=1, start_day__lte=31), name="budget_start_day_valid")]


class PersonalBudget(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    month = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2,
                                 validators=[MinValueValidator(Decimal("0.00"))])

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "month"], name="unique_personal_budget_month"),
            models.CheckConstraint(condition=models.Q(month__day=1), name="personal_budget_month_first_day"),
            models.CheckConstraint(condition=models.Q(amount__gte=0), name="personal_budget_nonnegative"),
        ]


class SavingsAccount(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2)
    started_on = models.DateField()


class SavingsMovement(models.Model):
    class Kind(models.TextChoices):
        DEPOSIT = "deposit", "Depunere"
        WITHDRAWAL = "withdrawal", "Retragere"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    occurred_on = models.DateField()
    description = models.CharField(max_length=200, blank=True)

class Income(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="incomes",
    )
    source = models.CharField(max_length=100)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    received_on = models.DateField()

    def __str__(self):
        return f"{self.source}: {self.amount}"

class Expense(models.Model):
    from_personal_budget = models.BooleanField(default=False)

    class Category(models.TextChoices):
        RENT = "rent", "Chirie"
        UTILITIES = "utilities", "Utilități"
        SUBSCRIPTIONS = "subscriptions", "Abonamente"
        FOOD = "food", "Alimentație"
        TRANSPORT = "transport", "Transport"
        OTHER = "other", "Altele"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="expenses",
    )
    name = models.CharField(max_length=100)
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    paid_on = models.DateField()

    def __str__(self):
        return f"{self.name}: {self.amount}"

class RecurringExpense(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=Expense.Category.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    payment_day = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(31)])
    starts_on = models.DateField()
    active = models.BooleanField(default=True)


class RecurringExpenseOccurrence(models.Model):
    rule = models.ForeignKey(RecurringExpense, on_delete=models.CASCADE)
    month = models.DateField()
    expense = models.OneToOneField(Expense, null=True, on_delete=models.SET_NULL)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["rule", "month"], name="unique_recurring_expense_month")]


class Installment(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="installments",
    )
    name = models.CharField(max_length=100)
    monthly_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    first_due_on = models.DateField()
    number_of_installments = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )

    def __str__(self):
        return f"{self.name}: {self.monthly_amount} lei/lună"

