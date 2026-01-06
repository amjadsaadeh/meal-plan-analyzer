from django import template

register = template.Library()

@register.filter
def divide_by_100_mult(value, arg):
    try:
        return (float(value) / 100) * float(arg)
    except (ValueError, TypeError):
        return 0
