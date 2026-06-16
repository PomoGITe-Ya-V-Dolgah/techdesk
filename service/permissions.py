from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from .models import Profile


def user_role(user) -> str:
    if not user.is_authenticated:
        return ""
    if user.is_superuser:
        return Profile.Role.ADMIN
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile.role


def has_role(user, *roles: str) -> bool:
    return user_role(user) in roles


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
