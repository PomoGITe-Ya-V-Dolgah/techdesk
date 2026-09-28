"""Вход с защитой от подбора пароля.

После LOGIN_MAX_FAILURES неудачных попыток с одного IP для одного логина вход
блокируется на LOGIN_LOCKOUT_MINUTES минут. Это важно, если techdesk доступен
из интернета.
"""

from django.conf import settings
from django.contrib.auth import views as auth_views
from django.core.cache import cache


def client_ip(request) -> str:
    # За Caddy сервер waitress сам подставляет в REMOTE_ADDR реальный IP клиента
    # (см. serve.py, trusted_proxy). Заголовок читаем только как запасной вариант.
    if settings.BEHIND_PROXY:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            # Последний адрес добавил наш прокси (Caddy) — ему можно доверять.
            return forwarded.split(",")[-1].strip()
    return request.META.get("REMOTE_ADDR", "")


def _key(request, username: str) -> str:
    return f"login-fail:{client_ip(request)}:{(username or '').lower()}"


class ThrottledLoginView(auth_views.LoginView):
    template_name = "registration/login.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_demo_logins"] = settings.SHOW_DEMO_LOGINS
        return context

    def post(self, request, *args, **kwargs):
        key = _key(request, request.POST.get("username"))
        if cache.get(key, 0) >= settings.LOGIN_MAX_FAILURES:
            form = self.get_form()
            form.add_error(
                None,
                f"Слишком много неудачных попыток. Попробуйте через {settings.LOGIN_LOCKOUT_MINUTES} мин.",
            )
            return self.render_to_response(self.get_context_data(form=form), status=429)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        key = _key(self.request, self.request.POST.get("username"))
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, settings.LOGIN_LOCKOUT_MINUTES * 60)
        return super().form_invalid(form)

    def form_valid(self, form):
        cache.delete(_key(self.request, self.request.POST.get("username")))
        return super().form_valid(form)
