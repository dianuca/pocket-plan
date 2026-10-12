from django import template

register = template.Library()
MONTHS = ("Ian", "Feb", "Mar", "Apr", "Mai", "Iun", "Iul", "Aug", "Sep", "Oct", "Noi", "Dec")


@register.filter
def budget_month_label(value):
    try:
        year, month = str(value).split("-")
        number = int(month)
        if 1 <= number <= 12:
            return f"{year}-{MONTHS[number - 1]}"
    except (ValueError, TypeError):
        pass
    return value
