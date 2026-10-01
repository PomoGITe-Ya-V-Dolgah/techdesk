from django.db.models import F


def sort_queryset(request, queryset, columns, default="name"):
    """Сортировка только по разрешённым полям, пустые значения в конце."""
    fields = {key: fields for key, _, fields in columns}
    sort = request.GET.get("sort", default)
    key = sort.removeprefix("-")
    if key not in fields:
        sort, key = default, default.removeprefix("-")
    descending = sort.startswith("-")
    ordering = [F(field).desc(nulls_last=True) if descending else F(field).asc(nulls_last=True) for field in fields[key]]
    queryset = queryset.order_by(*ordering, "pk")
    headers = [{"key": name, "label": label, "active": name == key,
                "direction": "descending" if descending else "ascending",
                "next": name if name == key and descending else "-" + name if name == key else name}
               for name, label, _ in columns]
    return queryset, sort, headers
