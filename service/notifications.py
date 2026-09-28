"""Уведомления по e-mail. Работают, только если в .env задан EMAIL_HOST."""

import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail

from .models import Profile

logger = logging.getLogger(__name__)


def _ticket_url(ticket) -> str:
    base = settings.PUBLIC_BASE_URL or ""
    return f"{base}{ticket.get_absolute_url()}"


def _send(subject: str, body: str, recipients) -> int:
    recipients = sorted({email for email in recipients if email})
    if not settings.EMAIL_HOST or not recipients:
        return 0
    try:
        return send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, recipients)
    except Exception:  # почта не должна ломать работу с заявками
        logger.exception("Не удалось отправить уведомление")
        return 0


def ticket_created(ticket) -> int:
    support = User.objects.filter(
        is_active=True,
        profile__role__in=[Profile.Role.OPERATOR, Profile.Role.ENGINEER, Profile.Role.ADMIN],
    ).values_list("email", flat=True)
    equipment = f"\nОборудование: {ticket.equipment}" if ticket.equipment_id else ""
    body = (
        f"Новая заявка #{ticket.pk}: {ticket.title}\n"
        f"Автор: {ticket.reporter.get_full_name() or ticket.reporter.username}{equipment}\n"
        f"Приоритет: {ticket.get_priority_display()}\n\n{ticket.description}\n\n{_ticket_url(ticket)}"
    )
    return _send(f"[techdesk] Новая заявка #{ticket.pk}: {ticket.title}", body, support)


def ticket_assigned(ticket) -> int:
    if not ticket.assignee:
        return 0
    body = f"Вам назначена заявка #{ticket.pk}: {ticket.title}\n\n{ticket.description}\n\n{_ticket_url(ticket)}"
    return _send(f"[techdesk] Назначена заявка #{ticket.pk}", body, [ticket.assignee.email])


def ticket_status_changed(ticket) -> int:
    body = f"Статус заявки #{ticket.pk} «{ticket.title}»: {ticket.get_status_display()}"
    if ticket.resolution_summary:
        body += f"\n\nРешение: {ticket.resolution_summary}"
    body += f"\n\n{_ticket_url(ticket)}"
    return _send(f"[techdesk] Заявка #{ticket.pk}: {ticket.get_status_display()}", body, [ticket.reporter.email])
