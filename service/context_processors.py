from .permissions import REGISTRY_ROLES, user_role


def role(request):
    """Роль текущего пользователя доступна во всех шаблонах как current_role."""
    current = user_role(request.user) if hasattr(request, "user") else ""
    return {
        "current_role": current,
        "is_support": current in ("admin", "operator", "engineer", "manager"),
        "can_edit_registry": current in REGISTRY_ROLES,
        "can_see_reports": current in ("admin", "manager"),
    }
