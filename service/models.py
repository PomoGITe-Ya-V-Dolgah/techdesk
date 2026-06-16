from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Department(models.Model):
    name = models.CharField("Название", max_length=160, unique=True)
    description = models.TextField("Описание", blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Подразделение"
        verbose_name_plural = "Подразделения"

    def __str__(self):
        return self.name


class Profile(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Администратор"
        OPERATOR = "operator", "Оператор"
        ENGINEER = "engineer", "Инженер"
        MANAGER = "manager", "Руководитель"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField("Роль", max_length=20, choices=Role.choices, default=Role.OPERATOR)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Подразделение")

    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"


class Location(models.Model):
    name = models.CharField("Наименование", max_length=160)
    building = models.CharField("Корпус", max_length=80, blank=True)
    floor = models.CharField("Этаж", max_length=20, blank=True)
    room = models.CharField("Кабинет", max_length=40, blank=True)

    class Meta:
        ordering = ["building", "floor", "room", "name"]
        verbose_name = "Место установки"
        verbose_name_plural = "Места установки"

    def __str__(self):
        parts = [self.building, self.floor, self.room, self.name]
        return " / ".join(part for part in parts if part)


class EquipmentCategory(models.Model):
    name = models.CharField("Название", max_length=120, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Категория оборудования"
        verbose_name_plural = "Категории оборудования"

    def __str__(self):
        return self.name


class Equipment(models.Model):
    class Criticality(models.TextChoices):
        LOW = "low", "Низкая"
        MEDIUM = "medium", "Средняя"
        HIGH = "high", "Высокая"
        CRITICAL = "critical", "Критическая"

    name = models.CharField("Наименование", max_length=180)
    inventory_number = models.CharField("Инвентарный номер", max_length=80, unique=True)
    serial_number = models.CharField("Серийный номер", max_length=120, blank=True)
    category = models.ForeignKey(EquipmentCategory, on_delete=models.PROTECT, verbose_name="Категория")
    location = models.ForeignKey(Location, on_delete=models.PROTECT, verbose_name="Место установки")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Ответственное подразделение")
    manufacturer = models.CharField("Производитель", max_length=120, blank=True)
    model = models.CharField("Модель", max_length=120, blank=True)
    criticality = models.CharField("Критичность", max_length=20, choices=Criticality.choices, default=Criticality.MEDIUM)
    notes = models.TextField("Примечание", blank=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        ordering = ["name", "inventory_number"]
        verbose_name = "Оборудование"
        verbose_name_plural = "Оборудование"

    def __str__(self):
        return f"{self.name} ({self.inventory_number})"

    def get_absolute_url(self):
        return reverse("equipment_detail", kwargs={"pk": self.pk})


class TicketCategory(models.Model):
    name = models.CharField("Название", max_length=120, unique=True)
    default_priority = models.CharField("Приоритет по умолчанию", max_length=20, choices=[
        ("low", "Низкий"),
        ("normal", "Обычный"),
        ("high", "Высокий"),
        ("urgent", "Срочный"),
    ], default="normal")

    class Meta:
        ordering = ["name"]
        verbose_name = "Категория заявки"
        verbose_name_plural = "Категории заявок"

    def __str__(self):
        return self.name


class Ticket(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новая"
        ASSIGNED = "assigned", "Назначена"
        IN_PROGRESS = "in_progress", "В работе"
        RESOLVED = "resolved", "Выполнена"
        CLOSED = "closed", "Закрыта"
        REJECTED = "rejected", "Отклонена"

    class Priority(models.TextChoices):
        LOW = "low", "Низкий"
        NORMAL = "normal", "Обычный"
        HIGH = "high", "Высокий"
        URGENT = "urgent", "Срочный"

    title = models.CharField("Тема", max_length=220)
    description = models.TextField("Описание проблемы")
    category = models.ForeignKey(TicketCategory, on_delete=models.PROTECT, verbose_name="Категория")
    equipment = models.ForeignKey(Equipment, on_delete=models.PROTECT, related_name="tickets", verbose_name="Оборудование")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reported_tickets", verbose_name="Автор")
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_tickets", verbose_name="Исполнитель")
    status = models.CharField("Статус", max_length=20, choices=Status.choices, default=Status.NEW)
    priority = models.CharField("Приоритет", max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    due_at = models.DateTimeField("Срок выполнения", null=True, blank=True)
    resolution_summary = models.TextField("Итоговое решение", blank=True)
    created_at = models.DateTimeField("Создана", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлена", auto_now=True)
    resolved_at = models.DateTimeField("Выполнена", null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"

    def __str__(self):
        return f"#{self.pk} {self.title}"

    def save(self, *args, **kwargs):
        if self.status in {self.Status.RESOLVED, self.Status.CLOSED} and not self.resolved_at:
            self.resolved_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        return bool(self.due_at and self.status not in {self.Status.RESOLVED, self.Status.CLOSED, self.Status.REJECTED} and self.due_at < timezone.now())

    @property
    def duration_hours(self):
        if not self.resolved_at:
            return None
        delta = self.resolved_at - self.created_at
        return round(delta.total_seconds() / 3600, 1)

    def get_absolute_url(self):
        return reverse("ticket_detail", kwargs={"pk": self.pk})


class TicketComment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="comments", verbose_name="Заявка")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name="Автор")
    text = models.TextField("Комментарий")
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"

    def __str__(self):
        return f"Комментарий к заявке #{self.ticket_id}"


class Solution(models.Model):
    ticket = models.OneToOneField(Ticket, on_delete=models.CASCADE, related_name="solution", verbose_name="Заявка")
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name="solutions", verbose_name="Оборудование")
    title = models.CharField("Краткое название", max_length=220)
    problem_summary = models.TextField("Краткое описание проблемы")
    resolution_steps = models.TextField("Шаги решения")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name="Автор решения")
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Типовое решение"
        verbose_name_plural = "Типовые решения"

    def __str__(self):
        return self.title

# Create your models here.
