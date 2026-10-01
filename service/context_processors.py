from .models import Profile
from .permissions import REGISTRY_ROLES, user_role


def role(request):
    """Роль текущего пользователя доступна во всех шаблонах как current_role."""
    current = user_role(request.user) if hasattr(request, "user") else ""
    preferences = None
    if hasattr(request, "user") and request.user.is_authenticated:
        profile, _ = Profile.objects.get_or_create(user=request.user)
        preferences = {"sound": profile.notification_sound, "scope": profile.notification_scope, "userId": request.user.pk}
    return {
        "notification_preferences": preferences,
        "current_role": current,
        "is_support": current in ("admin", "operator", "engineer", "manager"),
        "can_edit_registry": current in REGISTRY_ROLES,
        "can_see_reports": current in ("admin", "manager"),
    }
