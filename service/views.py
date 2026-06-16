import csv
from io import BytesIO

import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import EquipmentForm, TicketAssignForm, TicketCommentForm, TicketForm, TicketStatusForm
from .models import Equipment, Profile, Solution, Ticket
from .permissions import role_required, user_role
from .recommendations import recommend_solutions


@login_required
def dashboard(request):
    status_cards = [
        {"label": label, "value": Ticket.objects.filter(status=value).count(), "status": value}
        for value, label in Ticket.Status.choices
    ]
    context = {
        "status_cards": status_cards,
        "open_count": Ticket.objects.exclude(status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED, Ticket.Status.REJECTED]).count(),
        "overdue_count": Ticket.objects.filter(due_at__lt=timezone.now()).exclude(status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED, Ticket.Status.REJECTED]).count(),
        "equipment_count": Equipment.objects.count(),
        "recent_tickets": Ticket.objects.select_related("equipment", "assignee", "reporter")[:8],
        "top_equipment": Equipment.objects.annotate(ticket_count=Count("tickets")).filter(ticket_count__gt=0).order_by("-ticket_count")[:5],
        "role": user_role(request.user),
    }
    return render(request, "service/dashboard.html", context)


@login_required
def equipment_list(request):
    query = request.GET.get("q", "").strip()
    equipment = Equipment.objects.select_related("category", "location", "department")
    if query:
        equipment = equipment.filter(
            Q(name__icontains=query)
            | Q(inventory_number__icontains=query)
            | Q(serial_number__icontains=query)
            | Q(model__icontains=query)
        )
    return render(request, "service/equipment_list.html", {"equipment": equipment, "query": query, "role": user_role(request.user)})


@login_required
def equipment_detail(request, pk):
    equipment = get_object_or_404(Equipment.objects.select_related("category", "location", "department"), pk=pk)
    tickets = equipment.tickets.select_related("category", "assignee", "reporter")[:20]
    solutions = equipment.solutions.select_related("ticket", "created_by")[:10]
    create_url = reverse("ticket_create") + f"?equipment={equipment.pk}"
    return render(
        request,
        "service/equipment_detail.html",
        {"equipment": equipment, "tickets": tickets, "solutions": solutions, "create_url": create_url, "role": user_role(request.user)},
    )


@login_required
@role_required(Profile.Role.ADMIN, Profile.Role.OPERATOR, Profile.Role.MANAGER)
def equipment_create(request):
    form = EquipmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        equipment = form.save()
        messages.success(request, "Оборудование добавлено.")
        return redirect(equipment)
    return render(request, "service/form.html", {"form": form, "title": "Новое оборудование", "submit": "Сохранить"})


@login_required
@role_required(Profile.Role.ADMIN, Profile.Role.OPERATOR, Profile.Role.MANAGER)
def equipment_update(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    form = EquipmentForm(request.POST or None, instance=equipment)
    if request.method == "POST" and form.is_valid():
        equipment = form.save()
        messages.success(request, "Карточка оборудования обновлена.")
        return redirect(equipment)
    return render(request, "service/form.html", {"form": form, "title": "Редактирование оборудования", "submit": "Сохранить"})


@login_required
def equipment_qr(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    url = request.build_absolute_uri(reverse("ticket_create") + f"?equipment={equipment.pk}")
    image = qrcode.make(url)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    response = HttpResponse(buffer.getvalue(), content_type="image/png")
    response["Content-Disposition"] = f'inline; filename="equipment-{equipment.inventory_number}.png"'
    return response


@login_required
def ticket_list(request):
    tickets = Ticket.objects.select_related("equipment", "category", "assignee", "reporter")
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
        "equipment": Equipment.objects.all(),
        "role": user_role(request.user),
    }
    return render(request, "service/ticket_list.html", context)


@login_required
def ticket_create(request):
    initial = {}
    equipment_id = request.GET.get("equipment")
    if equipment_id:
        initial["equipment"] = equipment_id
    form = TicketForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        ticket = form.save(commit=False)
        ticket.reporter = request.user
        ticket.save()
        messages.success(request, "Заявка создана.")
        return redirect(ticket)
    return render(request, "service/form.html", {"form": form, "title": "Новая заявка", "submit": "Создать"})


@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket.objects.select_related("equipment", "category", "assignee", "reporter"), pk=pk)
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
        "recommendations": recommend_solutions(ticket),
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
        messages.success(request, "Исполнитель назначен.")
        return redirect(ticket)
    return render(request, "service/form.html", {"form": form, "title": "Назначение исполнителя", "submit": "Назначить"})


@login_required
def ticket_status(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if user_role(request.user) not in {Profile.Role.ADMIN, Profile.Role.ENGINEER, Profile.Role.MANAGER}:
        messages.error(request, "Недостаточно прав для изменения статуса.")
        return redirect(ticket)
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
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(["ID", "Тема", "Оборудование", "Статус", "Приоритет", "Автор", "Исполнитель", "Создана", "Выполнена", "Часы"])
    for ticket in Ticket.objects.select_related("equipment", "reporter", "assignee"):
        writer.writerow([
            ticket.id,
            ticket.title,
            ticket.equipment,
            ticket.get_status_display(),
            ticket.get_priority_display(),
            ticket.reporter.get_username(),
            ticket.assignee.get_username() if ticket.assignee else "",
            ticket.created_at.strftime("%Y-%m-%d %H:%M"),
            ticket.resolved_at.strftime("%Y-%m-%d %H:%M") if ticket.resolved_at else "",
            ticket.duration_hours or "",
        ])
    return response

# Create your views here.
