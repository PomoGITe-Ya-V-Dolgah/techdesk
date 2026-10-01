from django import template, forms

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


@register.simple_tag(takes_context=True)
def query_update(context, **changes):
    """Меняет параметры ссылки, сохраняя применённые фильтры."""
    query = context["request"].GET.copy()
    query.pop("partial", None)
    for key, value in changes.items():
        query[key] = str(value)
    return "?" + query.urlencode()


@register.filter
def is_textarea(widget):
    return isinstance(widget, forms.Textarea)
