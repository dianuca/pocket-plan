from django.conf import settings
from django.db import models


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