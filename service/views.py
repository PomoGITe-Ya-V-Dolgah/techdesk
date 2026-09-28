import csv
from io import BytesIO

import qrcode
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Prefetch, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import notifications
from .forms import (
    EquipmentForm,
    EquipmentImportForm,
    SoftwareInstallationForm,
    TicketAssignForm,
    TicketCommentForm,
    TicketForm,
    TicketStatusForm,
)
from .importers import import_equipment, template_csv
from .models import Equipment, EquipmentCategory, Location, Profile, Software, SoftwareInstallation, Solution, Ticket
from .permissions import REGISTRY_ROLES, is_support, role_required, user_role
from .recommendations import recommend_solutions

OPEN_STATUSES_EXCLUDED = [Ticket.Status.RESOLVED, Ticket.Status.CLOSED, Ticket.Status.REJECTED]


def visible_tickets(user):
    """Техотдел видит все заявки, сотрудник — только свои."""
    tickets = Ticket.objects.select_related("equipment", "category", "assignee", "reporter")
    if is_support(user):
        return tickets
    return tickets.filter(reporter=user)


@login_required
def dashboard(request):
    tickets = visible_tickets(request.user)
    status_cards = [
        {"label": label, "value": tickets.filter(status=value).count(), "status": value}
        for value, label in Ticket.Status.choices
    ]
    context = {
        "status_cards": status_cards,
        "open_count": tickets.exclude(status__in=OPEN_STATUSES_EXCLUDED).count(),
        "overdue_count": tickets.filter(due_at__lt=timezone.now()).exclude(status__in=OPEN_STATUSES_EXCLUDED).count(),
        "equipment_count": Equipment.objects.exclude(status=Equipment.Status.WRITTEN_OFF).count(),
        "recent_tickets": tickets[:8],
        "top_equipment": Equipment.objects.annotate(ticket_count=Count("tickets")).filter(ticket_count__gt=0).order_by("-ticket_count")[:5],
        "my_equipment": Equipment.objects.filter(assigned_user=request.user).select_related("location", "category"),
        "role": user_role(request.user),
    }
    return render(request, "service/dashboard.html", context)


@login_required
def equipment_list(request):
    filters = {
        "q": request.GET.get("q", "").strip(),
        "category": request.GET.get("category", "").strip(),
        "location": request.GET.get("location", "").strip(),
        "status": request.GET.get("status", "").strip(),
    }
    equipment = Equipment.objects.select_related("category", "location", "department", "assigned_user")
    if filters["q"]:
        q = filters["q"]
        equipment = equipment.filter(
            Q(name__icontains=q)
            | Q(inventory_number__icontains=q)
            | Q(serial_number__icontains=q)
            | Q(model__icontains=q)
            | Q(hostname__icontains=q)
            | Q(ip_address__icontains=q)
            | Q(assigned_user__first_name__icontains=q)
            | Q(assigned_user__last_name__icontains=q)
            | Q(assigned_user__username__icontains=q)
            | Q(installations__software__name__icontains=q)
        ).distinct()
    if filters["category"]:
        equipment = equipment.filter(category_id=filters["category"])
    if filters["location"]:
        equipment = equipment.filter(location_id=filters["location"])
    if filters["status"]:
        equipment = equipment.filter(status=filters["status"])
    elif not filters["q"]:
        equipment = equipment.exclude(status=Equipment.Status.WRITTEN_OFF)
    context = {
        "equipment": equipment,
        "query": filters["q"],
        "filters": filters,
        "categories": EquipmentCategory.objects.all(),
        "locations": Location.objects.all(),
        "statuses": Equipment.Status.choices,
        "role": user_role(request.user),
    }
    return render(request, "service/equipment_list.html", context)


@login_required
def locations_overview(request):
    """«Что где стоит»: кабинеты, техника в них и кто за ней работает."""
    active = Equipment.objects.exclude(status=Equipment.Status.WRITTEN_OFF).select_related("category", "assigned_user").order_by("category__name", "name")
    locations = Location.objects.prefetch_related(Prefetch("equipment_set", queryset=active, to_attr="items"))
    return render(request, "service/locations.html", {"locations": locations})


@login_required
def equipment_detail(request, pk):
    equipment = get_object_or_404(
        Equipment.objects.select_related("category", "location", "department", "assigned_user", "parent"), pk=pk
    )
    tickets = visible_tickets(request.user).filter(equipment=equipment)[:20]
    solutions = equipment.solutions.select_related("ticket", "created_by")[:10] if is_support(request.user) else []
    create_url = reverse("ticket_create") + f"?equipment={equipment.pk}"
    context = {
        "equipment": equipment,
        "tickets": tickets,
        "solutions": solutions,
        "children": equipment.children.select_related("category"),
        "installations": equipment.installations.select_related("software"),
        "software_form": SoftwareInstallationForm(),
        "software_names": Software.objects.values_list("name", flat=True),
        "create_url": create_url,
        "role": user_role(request.user),
    }
    return render(request, "service/equipment_detail.html", context)


@login_required
@role_required(*REGISTRY_ROLES)
def equipment_create(request):
    form = EquipmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        equipment = form.save()
        messages.success(request, "Оборудование добавлено.")
        return redirect(equipment)
    return render(request, "service/form.html", {"form": form, "title": "Новое оборудование", "submit": "Сохранить"})


@login_required
@role_required(*REGISTRY_ROLES)
def equipment_update(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    form = EquipmentForm(request.POST or None, instance=equipment)
    if request.method == "POST" and form.is_valid():
        equipment = form.save()
        messages.success(request, "Карточка оборудования обновлена.")
        return redirect(equipment)
    return render(request, "service/form.html", {"form": form, "title": "Редактирование оборудования", "submit": "Сохранить"})


@login_required
@role_required(*REGISTRY_ROLES)
@require_POST
def equipment_software_add(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    form = SoftwareInstallationForm(request.POST)
    if form.is_valid():
        installation = form.save(equipment)
        messages.success(request, f"Добавлено ПО: {installation.software}.")
    else:
        messages.error(request, "Укажите название программы.")
    return redirect(equipment)


@login_required
@role_required(*REGISTRY_ROLES)
@require_POST
def equipment_software_remove(request, pk, installation_pk):
    installation = get_object_or_404(SoftwareInstallation, pk=installation_pk, equipment_id=pk)
    installation.delete()
    messages.success(request, f"ПО «{installation.software}» удалено из карточки.")
    return redirect(installation.equipment)


@login_required
@role_required(*REGISTRY_ROLES)
def equipment_import(request):
    form = EquipmentImportForm(request.POST or None, request.FILES or None)
    result = None
    if request.method == "POST" and form.is_valid():
        upload = form.cleaned_data["file"]
        result = import_equipment(upload.name, upload.read())
        if result.created or result.updated:
            messages.success(request, f"Импорт завершен: добавлено {result.created}, обновлено {result.updated}.")
    return render(request, "service/equipment_import.html", {"form": form, "result": result})


@login_required
def equipment_import_template(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="equipment-template.csv"'
    response.write("﻿" + template_csv())
    return response


@login_required
@role_required(*REGISTRY_ROLES)
def equipment_labels(request):
    """Лист наклеек с QR-кодами для печати (A4, 3 колонки)."""
    equipment = Equipment.objects.exclude(status=Equipment.Status.WRITTEN_OFF).select_related("location")
    location = request.GET.get("location", "").strip()
    if location:
        equipment = equipment.filter(location_id=location)
    context = {"equipment": equipment, "locations": Location.objects.all(), "location": location}
    return render(request, "service/equipment_labels.html", context)


@login_required
def equipment_qr(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    path = reverse("ticket_create") + f"?equipment={equipment.pk}"
    # В локальной сети QR должен вести на адрес сервера, а не на localhost того, кто печатает наклейку.
    url = f"{settings.PUBLIC_BASE_URL}{path}" if settings.PUBLIC_BASE_URL else request.build_absolute_uri(path)
    image = qrcode.make(url)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    response = HttpResponse(buffer.getvalue(), content_type="image/png")
    response["Content-Disposition"] = f'inline; filename="equipment-{equipment.inventory_number}.png"'
    return response


@login_required
def ticket_list(request):
    tickets = visible_tickets(request.user)
    filters = {
        "status": request.GET.get("status", "").strip(),
        "assignee": request.GET.get("assignee", "").strip(),
        "equipment": request.GET.get("equipment", "").strip(),
        "q": request.GET.get("q", "").strip(),
    }
    if filters["status"]:
        tickets = tickets.filter(status=filters["status"])
    if filters["assignee"]:
        tickets = tickets.filter(assignee_id=filters["assignee"])
    if filters["equipment"]:
        tickets = tickets.filter(equipment_id=filters["equipment"])
    if filters["q"]:
        tickets = tickets.filter(Q(title__icontains=filters["q"]) | Q(description__icontains=filters["q"]) | Q(equipment__name__icontains=filters["q"]))
    context = {
        "tickets": tickets,
        "filters": filters,
        "statuses": Ticket.Status.choices,
        "engineers": User.objects.filter(profile__role=Profile.Role.ENGINEER),
        "equipment": Equipment.objects.exclude(status=Equipment.Status.WRITTEN_OFF),
        "role": user_role(request.user),
    }
    return render(request, "service/ticket_list.html", context)


@login_required
def ticket_create(request):
    initial = {}
    equipment_id = request.GET.get("equipment")
    if equipment_id:
        initial["equipment"] = equipment_id
    simple = not is_support(request.user)
    form = TicketForm(request.POST or None, initial=initial, simple=simple)
    if request.method == "POST" and form.is_valid():
        ticket = form.save(commit=False)
        ticket.reporter = request.user
        ticket.save()
        notifications.ticket_created(ticket)
        messages.success(request, f"Заявка #{ticket.pk} создана. Статус можно отслеживать здесь.")
        return redirect(ticket)
    return render(request, "service/form.html", {"form": form, "title": "Новая заявка", "submit": "Создать"})


@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(visible_tickets(request.user), pk=pk)
    comment_form = TicketCommentForm(request.POST or None)
    if request.method == "POST" and comment_form.is_valid():
        comment = comment_form.save(commit=False)
        comment.ticket = ticket
        comment.author = request.user
        comment.save()
        messages.success(request, "Комментарий добавлен.")
        return redirect(ticket)
    context = {
        "ticket": ticket,
        "comment_form": comment_form,
        "comments": ticket.comments.select_related("author"),
        "recommendations": recommend_solutions(ticket) if is_support(request.user) else [],
        "role": user_role(request.user),
    }
    return render(request, "service/ticket_detail.html", context)


@login_required
@role_required(Profile.Role.ADMIN, Profile.Role.OPERATOR, Profile.Role.MANAGER)
def ticket_assign(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    form = TicketAssignForm(request.POST or None, instance=ticket)
    if request.method == "POST" and form.is_valid():
        ticket = form.save(commit=False)
        if ticket.status == Ticket.Status.NEW:
            ticket.status = Ticket.Status.ASSIGNED
        ticket.save()
        notifications.ticket_assigned(ticket)
        messages.success(request, "Исполнитель назначен.")
        return redirect(ticket)
    return render(request, "service/form.html", {"form": form, "title": "Назначение исполнителя", "submit": "Назначить"})


@login_required
def ticket_status(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if user_role(request.user) not in {Profile.Role.ADMIN, Profile.Role.ENGINEER, Profile.Role.MANAGER}:
        messages.error(request, "Недостаточно прав для изменения статуса.")
        return redirect("dashboard")
    old_status = ticket.status
    form = TicketStatusForm(request.POST or None, instance=ticket)
    if request.method == "POST" and form.is_valid():
        ticket = form.save()
        if ticket.status in {Ticket.Status.RESOLVED, Ticket.Status.CLOSED}:
            Solution.objects.update_or_create(
                ticket=ticket,
                defaults={
                    "equipment": ticket.equipment,
                    "title": ticket.title,
                    "problem_summary": ticket.description,
                    "resolution_steps": ticket.resolution_summary,
                    "created_by": request.user,
                },
            )
        if ticket.status != old_status:
            notifications.ticket_status_changed(ticket)
        messages.success(request, "Статус заявки обновлен.")
        return redirect(ticket)
    return render(request, "service/form.html", {"form": form, "title": "Изменение статуса", "submit": "Сохранить"})


@login_required
@role_required(Profile.Role.ADMIN, Profile.Role.MANAGER)
def reports(request):
    status_rows = Ticket.objects.values("status").annotate(count=Count("id")).order_by("status")
    equipment_rows = Equipment.objects.annotate(ticket_count=Count("tickets")).filter(ticket_count__gt=0).order_by("-ticket_count")[:20]
    engineer_rows = User.objects.filter(assigned_tickets__isnull=False).annotate(ticket_count=Count("assigned_tickets")).order_by("-ticket_count")
    context = {
        "status_rows": status_rows,
        "equipment_rows": equipment_rows,
        "engineer_rows": engineer_rows,
        "status_labels": dict(Ticket.Status.choices),
    }
    return render(request, "service/reports.html", context)


@login_required
@role_required(Profile.Role.ADMIN, Profile.Role.MANAGER)
def reports_export_csv(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="tickets-report.csv"'
    response.write("﻿")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(["ID", "Тема", "Оборудование", "Статус", "Приоритет", "Автор", "Исполнитель", "Создана", "Выполнена", "Часы"])
    for ticket in Ticket.objects.select_related("equipment", "reporter", "assignee"):
        writer.writerow([
            ticket.id,
            ticket.title,
            ticket.equipment or "",
            ticket.get_status_display(),
            ticket.get_priority_display(),
            ticket.reporter.get_username(),
            ticket.assignee.get_username() if ticket.assignee else "",
            timezone.localtime(ticket.created_at).strftime("%Y-%m-%d %H:%M"),
            timezone.localtime(ticket.resolved_at).strftime("%Y-%m-%d %H:%M") if ticket.resolved_at else "",
            ticket.duration_hours or "",
        ])
    return response


@login_required
@role_required(*REGISTRY_ROLES)
def equipment_export_csv(request):
    """Выгрузка реестра в формате, который можно загрузить обратно через импорт."""
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="equipment-registry.csv"'
    response.write("﻿")
    writer = csv.writer(response, delimiter=";")
    from .importers import TEMPLATE_HEADER

    writer.writerow(TEMPLATE_HEADER)
    items = Equipment.objects.select_related("category", "location", "department", "assigned_user", "parent").prefetch_related("installations__software")
    for item in items:
        writer.writerow([
            item.inventory_number,
            item.name,
            item.category.name,
            item.location.name,
            item.assigned_user.username if item.assigned_user else "",
            item.department.name if item.department else "",
            item.get_status_display(),
            item.manufacturer,
            item.model,
            item.serial_number,
            item.hostname,
            item.ip_address or "",
            item.mac_address,
            item.operating_system,
            ", ".join(inst.software.name for inst in item.installations.all()),
            item.parent.inventory_number if item.parent else "",
            item.notes,
        ])
    return response
