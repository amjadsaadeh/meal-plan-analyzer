from django import template

register = template.Library()


@register.filter
def divide_by_100_mult(value, arg):
    try:
        return (float(value) / 100) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def split_to_dict(value):
    """
    Splits a string like 'key:val,key2:val2' into a list of tuples for iteration.
    """
    try:
        items = value.split(",")
        return [item.split(":") for item in items]
    except Exception:
        return []


@register.filter
def get_item(dictionary, key):
    if not dictionary:
        return None
    return dictionary.get(key)


@register.filter
def get_attr(obj, attr_name):
    return getattr(obj, attr_name, 0.0)
