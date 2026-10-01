from functools import wraps

from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import redirect

from .models import Profile

# Роли технического отдела: видят все заявки и весь реестр.
SUPPORT_ROLES = (Profile.Role.ADMIN, Profile.Role.OPERATOR, Profile.Role.ENGINEER, Profile.Role.MANAGER)
# Роли, которые ведут реестр оборудования.
REGISTRY_ROLES = (Profile.Role.ADMIN, Profile.Role.OPERATOR, Profile.Role.MANAGER)


def user_role(user) -> str:
    if not user.is_authenticated:
        return ""
    if user.is_superuser:
        return Profile.Role.ADMIN
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile.role


def has_role(user, *roles: str) -> bool:
    return user_role(user) in roles


def is_support(user) -> bool:
    return has_role(user, *SUPPORT_ROLES)


def role_required(*roles: str):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if has_role(request.user, *roles):
                return view_func(request, *args, **kwargs)
            messages.error(request, "Недостаточно прав для выполнения действия.")
            return redirect("dashboard")

        return wrapper

    return decorator


EXECUTOR_ROLES = (Profile.Role.ENGINEER, Profile.Role.ADMIN)


def eligible_assignees():
    return User.objects.filter(is_active=True).filter(
        Q(profile__role__in=EXECUTOR_ROLES) | Q(is_superuser=True)
    ).select_related("profile").order_by("last_name", "first_name", "username")


def assignee_label(user):
    role = "Администратор" if user.is_superuser else user.profile.get_role_display()
    return f"{user.get_full_name() or user.username} — {role}"
