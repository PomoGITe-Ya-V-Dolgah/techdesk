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
        EMPLOYEE = "employee", "Сотрудник"
        OPERATOR = "operator", "Оператор"
        ENGINEER = "engineer", "Инженер"
        MANAGER = "manager", "Руководитель"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField("Роль", max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    notification_sound = models.BooleanField("Звук уведомлений", default=False)
    notification_scope = models.CharField("События для звука", max_length=20, choices=[("all", "Все новые заявки"), ("assigned", "Назначенные мне")], default="assigned")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Подразделение")
    position = models.CharField("Должность", max_length=120, blank=True)
    phone = models.CharField("Телефон (внутренний)", max_length=40, blank=True)

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

    class Status(models.TextChoices):
        IN_USE = "in_use", "В работе"
        STOCK = "stock", "На складе"
        REPAIR = "repair", "В ремонте"
        WRITTEN_OFF = "written_off", "Списано"

    name = models.CharField("Наименование", max_length=180)
    inventory_number = models.CharField("Инвентарный номер", max_length=80, unique=True)
    serial_number = models.CharField("Серийный номер", max_length=120, blank=True)
    category = models.ForeignKey(EquipmentCategory, on_delete=models.PROTECT, verbose_name="Категория")
    location = models.ForeignKey(Location, on_delete=models.PROTECT, verbose_name="Место установки")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Ответственное подразделение")
    manufacturer = models.CharField("Производитель", max_length=120, blank=True)
    model = models.CharField("Модель", max_length=120, blank=True)
    criticality = models.CharField("Критичность", max_length=20, choices=Criticality.choices, default=Criticality.MEDIUM)
    status = models.CharField("Статус", max_length=20, choices=Status.choices, default=Status.IN_USE)
    assigned_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_equipment",
        verbose_name="Сотрудник (за кем закреплено)",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="Подключено к / установлено на",
        help_text="Например: монитор — к ПК, виртуальная машина — к серверу.",
    )
    hostname = models.CharField("Имя компьютера в сети", max_length=120, blank=True)
    ip_address = models.GenericIPAddressField("IP-адрес", null=True, blank=True)
    mac_address = models.CharField("MAC-адрес", max_length=40, blank=True)
    operating_system = models.CharField("Операционная система", max_length=120, blank=True)
    purchase_date = models.DateField("Дата покупки", null=True, blank=True)
    warranty_until = models.DateField("Гарантия до", null=True, blank=True)
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


class Software(models.Model):
    class LicenseType(models.TextChoices):
        FREE = "free", "Бесплатное"
        COMMERCIAL = "commercial", "Коммерческая лицензия"
        SUBSCRIPTION = "subscription", "Подписка"
        UNKNOWN = "unknown", "Не указано"

    name = models.CharField("Название", max_length=160, unique=True)
    vendor = models.CharField("Разработчик", max_length=120, blank=True)
    license_type = models.CharField("Тип лицензии", max_length=20, choices=LicenseType.choices, default=LicenseType.UNKNOWN)
    notes = models.TextField("Примечание", blank=True, help_text="Где лежит лицензия, кто продлевает. Ключи здесь не храните.")

    class Meta:
        ordering = ["name"]
        verbose_name = "Программа"
        verbose_name_plural = "Программы"

    def __str__(self):
        return self.name


class SoftwareInstallation(models.Model):
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name="installations", verbose_name="Оборудование")
    software = models.ForeignKey(Software, on_delete=models.PROTECT, related_name="installations", verbose_name="Программа")
    version = models.CharField("Версия", max_length=60, blank=True)
    license_until = models.DateField("Лицензия до", null=True, blank=True)
    installed_at = models.DateField("Установлено", null=True, blank=True)

    class Meta:
        ordering = ["software__name"]
        unique_together = [("equipment", "software")]
        verbose_name = "Установленная программа"
        verbose_name_plural = "Установленные программы"

    def __str__(self):
        return f"{self.software} на {self.equipment}"


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
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="tickets",
        verbose_name="Оборудование",
        help_text="Можно не указывать, если вопрос не про конкретное устройство (доступы, почта, 1С).",
    )
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
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, null=True, blank=True, related_name="solutions", verbose_name="Оборудование")
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



class TicketEvent(models.Model):
    """События создания и назначения для уведомлений в открытом браузере."""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="events")
    kind = models.CharField(max_length=20, choices=[("created", "Создана"), ("assigned", "Назначена")])
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="ticket_events_created")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="ticket_events_received")
    created_at = models.DateTimeField(auto_now_add=True)
