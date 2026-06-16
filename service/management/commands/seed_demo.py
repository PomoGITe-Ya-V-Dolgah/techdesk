from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from service.models import (
    Department,
    Equipment,
    EquipmentCategory,
    Location,
    Profile,
    Solution,
    Ticket,
    TicketCategory,
    TicketComment,
)


class Command(BaseCommand):
    help = "Creates demo users and data for the VКR Service Desk application."

    def handle(self, *args, **options):
        support, _ = Department.objects.get_or_create(name="Отдел технического обслуживания")
        accounting, _ = Department.objects.get_or_create(name="Бухгалтерия")
        education, _ = Department.objects.get_or_create(name="Учебная часть")

        users = {
            "admin": self.user("admin", "admin123", "Анна", "Администратор", Profile.Role.ADMIN, support, True),
            "operator": self.user("operator", "operator123", "Ольга", "Оператор", Profile.Role.OPERATOR, support),
            "engineer": self.user("engineer", "engineer123", "Иван", "Инженер", Profile.Role.ENGINEER, support),
            "manager": self.user("manager", "manager123", "Мария", "Руководитель", Profile.Role.MANAGER, support),
        }

        printer_cat, _ = EquipmentCategory.objects.get_or_create(name="Принтер")
        network_cat, _ = EquipmentCategory.objects.get_or_create(name="Сетевое оборудование")
        pc_cat, _ = EquipmentCategory.objects.get_or_create(name="Рабочая станция")
        ticket_printer, _ = TicketCategory.objects.get_or_create(name="Печать", defaults={"default_priority": Ticket.Priority.NORMAL})
        ticket_network, _ = TicketCategory.objects.get_or_create(name="Сеть", defaults={"default_priority": Ticket.Priority.HIGH})
        ticket_pc, _ = TicketCategory.objects.get_or_create(name="Рабочее место", defaults={"default_priority": Ticket.Priority.NORMAL})

        room_205, _ = Location.objects.get_or_create(name="Кабинет 205", building="Главный корпус", floor="2", room="205")
        room_112, _ = Location.objects.get_or_create(name="Кабинет 112", building="Главный корпус", floor="1", room="112")

        printer, _ = Equipment.objects.get_or_create(
            inventory_number="PRN-205-001",
            defaults={
                "name": "Принтер HP LaserJet 205",
                "serial_number": "SN-HP-205-001",
                "category": printer_cat,
                "location": room_205,
                "department": accounting,
                "manufacturer": "HP",
                "model": "LaserJet Pro",
                "criticality": Equipment.Criticality.MEDIUM,
            },
        )
        router, _ = Equipment.objects.get_or_create(
            inventory_number="NET-112-001",
            defaults={
                "name": "Маршрутизатор MikroTik",
                "serial_number": "SN-MTK-112-001",
                "category": network_cat,
                "location": room_112,
                "department": education,
                "manufacturer": "MikroTik",
                "model": "RB4011",
                "criticality": Equipment.Criticality.HIGH,
            },
        )
        pc, _ = Equipment.objects.get_or_create(
            inventory_number="PC-205-014",
            defaults={
                "name": "Рабочая станция бухгалтера",
                "serial_number": "SN-PC-205-014",
                "category": pc_cat,
                "location": room_205,
                "department": accounting,
                "manufacturer": "Lenovo",
                "model": "ThinkCentre",
                "criticality": Equipment.Criticality.MEDIUM,
            },
        )

        closed = self.ticket(
            title="Принтер не печатает документы",
            description="При отправке документа на печать появляется ошибка очереди печати. Бумага есть, тонер установлен.",
            category=ticket_printer,
            equipment=printer,
            reporter=users["operator"],
            assignee=users["engineer"],
            status=Ticket.Status.CLOSED,
            priority=Ticket.Priority.NORMAL,
            resolution="Очищена очередь печати, перезапущена служба печати, переустановлен драйвер устройства.",
        )
        Solution.objects.update_or_create(
            ticket=closed,
            defaults={
                "equipment": printer,
                "title": closed.title,
                "problem_summary": closed.description,
                "resolution_steps": closed.resolution_summary,
                "created_by": users["engineer"],
            },
        )

        self.ticket(
            title="Нет доступа к сети в кабинете 112",
            description="Компьютеры периодически теряют подключение к локальной сети и интернету.",
            category=ticket_network,
            equipment=router,
            reporter=users["operator"],
            assignee=users["engineer"],
            status=Ticket.Status.IN_PROGRESS,
            priority=Ticket.Priority.HIGH,
        )
        self.ticket(
            title="Медленно запускается рабочая станция",
            description="После включения компьютер долго загружает профиль пользователя и бухгалтерскую программу.",
            category=ticket_pc,
            equipment=pc,
            reporter=users["operator"],
            assignee=users["engineer"],
            status=Ticket.Status.ASSIGNED,
            priority=Ticket.Priority.NORMAL,
            due_at=timezone.now() + timedelta(days=1),
        )
        TicketComment.objects.get_or_create(ticket=closed, author=users["engineer"], text="Проверена печать тестовой страницы, проблема не повторяется.")

        self.stdout.write(self.style.SUCCESS("Demo data created. Login: admin/admin123, operator/operator123, engineer/engineer123, manager/manager123"))

    def user(self, username, password, first_name, last_name, role, department, is_superuser=False):
        user, created = User.objects.get_or_create(username=username, defaults={"first_name": first_name, "last_name": last_name})
        if created:
            user.set_password(password)
        user.first_name = first_name
        user.last_name = last_name
        user.is_staff = role == Profile.Role.ADMIN or is_superuser
        user.is_superuser = is_superuser
        user.save()
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.role = role
        profile.department = department
        profile.save()
        return user

    def ticket(self, **kwargs):
        resolution = kwargs.pop("resolution", "")
        ticket, _ = Ticket.objects.get_or_create(
            title=kwargs["title"],
            equipment=kwargs["equipment"],
            defaults={**kwargs, "resolution_summary": resolution},
        )
        if resolution and not ticket.resolution_summary:
            ticket.resolution_summary = resolution
            ticket.save()
        return ticket
