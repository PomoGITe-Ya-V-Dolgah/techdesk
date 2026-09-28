from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    return mapping.get(key, key)


@register.filter
def person(user, empty=""):
    """ФИО пользователя или логин; пустая строка/значение empty, если пользователя нет."""
    if not user:
        return empty
    return user.get_full_name() or user.get_username()
