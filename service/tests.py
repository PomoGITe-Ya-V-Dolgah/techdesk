from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Department, Equipment, EquipmentCategory, Location, Profile, Solution, Ticket, TicketCategory
from .recommendations import recommend_solutions


class ServiceDeskTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="Отдел ТО")
        self.location = Location.objects.create(name="Кабинет 101")
        self.equipment_category = EquipmentCategory.objects.create(name="Принтер")
        self.ticket_category = TicketCategory.objects.create(name="Печать")
        self.operator = User.objects.create_user(username="operator", password="pass")
        self.engineer = User.objects.create_user(username="engineer", password="pass")
        Profile.objects.create(user=self.operator, role=Profile.Role.OPERATOR, department=self.department)
        Profile.objects.create(user=self.engineer, role=Profile.Role.ENGINEER, department=self.department)
        self.equipment = Equipment.objects.create(
            name="Принтер HP",
            inventory_number="PRN-001",
            category=self.equipment_category,
            location=self.location,
            department=self.department,
        )

    def test_create_ticket_from_view(self):
        self.client.force_login(self.operator)
        response = self.client.post(
            reverse("ticket_create"),
            {
                "title": "Принтер не печатает",
                "description": "Документ остается в очереди печати",
                "category": self.ticket_category.id,
                "equipment": self.equipment.id,
                "priority": Ticket.Priority.NORMAL,
                "due_at": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        ticket = Ticket.objects.get(title="Принтер не печатает")
        self.assertEqual(ticket.reporter, self.operator)
        self.assertEqual(ticket.status, Ticket.Status.NEW)

    def test_close_ticket_creates_solution(self):
        ticket = Ticket.objects.create(
            title="Принтер не печатает",
            description="Ошибка очереди печати",
            category=self.ticket_category,
            equipment=self.equipment,
            reporter=self.operator,
            assignee=self.engineer,
        )
        self.client.force_login(self.engineer)
        response = self.client.post(
            reverse("ticket_status", kwargs={"pk": ticket.pk}),
            {"status": Ticket.Status.RESOLVED, "resolution_summary": "Очищена очередь печати и перезапущена служба."},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Solution.objects.filter(ticket=ticket).exists())

    def test_recommendations_use_equipment_category_and_keywords(self):
        old_ticket = Ticket.objects.create(
            title="Принтер не печатает",
            description="Ошибка очереди печати",
            category=self.ticket_category,
            equipment=self.equipment,
            reporter=self.operator,
            assignee=self.engineer,
            status=Ticket.Status.CLOSED,
            resolution_summary="Очищена очередь печати.",
        )
        Solution.objects.create(
            ticket=old_ticket,
            equipment=self.equipment,
            title=old_ticket.title,
            problem_summary=old_ticket.description,
            resolution_steps=old_ticket.resolution_summary,
            created_by=self.engineer,
        )
        new_ticket = Ticket.objects.create(
            title="Не печатает отчет",
            description="В очереди печати висит документ",
            category=self.ticket_category,
            equipment=self.equipment,
            reporter=self.operator,
        )
        recommendations = recommend_solutions(new_ticket)
        self.assertEqual(len(recommendations), 1)
        self.assertGreaterEqual(recommendations[0].score, 85)

    def test_operator_cannot_open_reports(self):
        self.client.force_login(self.operator)
        response = self.client.get(reverse("reports"))
        self.assertEqual(response.status_code, 302)

# Create your tests here.


class LanDeploymentTests(TestCase):
    """Проверки настроек для работы в локальной сети."""

    def setUp(self):
        self.user = User.objects.create_user(username="lan", password="pass")
        Profile.objects.create(user=self.user, role=Profile.Role.OPERATOR)
        self.equipment = Equipment.objects.create(
            name="МФУ",
            inventory_number="MFU-001",
            category=EquipmentCategory.objects.create(name="МФУ"),
            location=Location.objects.create(name="Кабинет 1"),
        )

    def test_qr_uses_public_base_url(self):
        from io import BytesIO
        from unittest import mock

        self.client.force_login(self.user)
        with self.settings(PUBLIC_BASE_URL="http://192.168.1.10:8000"), mock.patch("service.views.qrcode.make") as make:
            make.return_value.save.side_effect = lambda buffer, format: buffer.write(b"png")
            response = self.client.get(reverse("equipment_qr", args=[self.equipment.pk]))
        self.assertEqual(response.status_code, 200)
        make.assert_called_once_with(f"http://192.168.1.10:8000/tickets/create/?equipment={self.equipment.pk}")

    def test_login_page_hides_demo_passwords(self):
        from django.contrib.auth import views as auth_views

        response = auth_views.LoginView.as_view(
            template_name="registration/login.html",
            extra_context={"show_demo_logins": False},
        )(self._get("/login/"))
        response.render()
        self.assertNotIn("admin123", response.content.decode())

    def test_bootstrap_served_locally(self):
        response = self.client.get(reverse("login"))
        self.assertNotContains(response, "cdn.jsdelivr.net")
        self.assertContains(response, "vendor/bootstrap/bootstrap.min.css")

    def _get(self, path):
        from django.test import RequestFactory
        from django.contrib.auth.models import AnonymousUser

        request = RequestFactory().get(path)
        request.user = AnonymousUser()
        return request


class EmployeeAndRegistryTests(TestCase):
    """Роль «Сотрудник», заявки без оборудования, реестр и импорт."""

    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.location = Location.objects.create(name="Кабинет 205")
        self.category = EquipmentCategory.objects.create(name="Рабочая станция")
        self.ticket_category = TicketCategory.objects.create(name="Доступы")
        self.employee = User.objects.create_user(username="petrova", password="pass", first_name="Елена", last_name="Петрова")
        self.other = User.objects.create_user(username="ivanov", password="pass")
        self.engineer = User.objects.create_user(username="eng", password="pass")
        Profile.objects.create(user=self.engineer, role=Profile.Role.ENGINEER)
        self.pc = Equipment.objects.create(
            name="ПК бухгалтера", inventory_number="PC-1", category=self.category, location=self.location, assigned_user=self.employee
        )

    def test_new_user_gets_employee_role(self):
        from .permissions import user_role

        self.assertEqual(user_role(self.employee), Profile.Role.EMPLOYEE)

    def test_employee_creates_ticket_without_equipment(self):
        self.client.force_login(self.employee)
        response = self.client.post(
            reverse("ticket_create"),
            {"title": "Доступ к папке", "description": "Нужен доступ", "category": self.ticket_category.id, "equipment": "", "priority": "normal"},
        )
        self.assertEqual(response.status_code, 302)
        ticket = Ticket.objects.get(title="Доступ к папке")
        self.assertIsNone(ticket.equipment)
        self.assertEqual(recommend_solutions(ticket), [])

    def test_employee_sees_only_own_tickets(self):
        own = Ticket.objects.create(title="Мой", description="-", category=self.ticket_category, reporter=self.employee)
        alien = Ticket.objects.create(title="Чужой", description="-", category=self.ticket_category, reporter=self.other)
        self.client.force_login(self.employee)
        response = self.client.get(reverse("ticket_list"))
        self.assertContains(response, "Мой")
        self.assertNotContains(response, "Чужой")
        self.assertEqual(self.client.get(reverse("ticket_detail", args=[alien.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("ticket_detail", args=[own.pk])).status_code, 200)

    def test_employee_cannot_edit_equipment(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse("equipment_update", args=[self.pc.pk]))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_shows_my_equipment(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Закреплено за мной")
        self.assertContains(response, "ПК бухгалтера")

    def test_locations_overview(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse("locations_overview"))
        self.assertContains(response, "Кабинет 205")
        self.assertContains(response, "Петрова")

    def test_import_csv_from_russian_excel(self):
        from .importers import import_equipment

        data = (
            "Инв. номер;Название;Категория;Кабинет;Сотрудник;IP;ПО;Подключено к\n"
            "MON-1;Монитор;Монитор;Кабинет 205;Петрова Елена;;;PC-1\n"
            "PC-1;ПК бухгалтера (обновлено);Рабочая станция;Кабинет 205;petrova;192.168.1.21;1С:Предприятие, Microsoft Office;\n"
            "SRV-1;Сервер;Сервер;Серверная;Неизвестный Человек;999.1.1.1;;\n"
        ).encode("cp1251")
        result = import_equipment("реестр.csv", data)
        self.assertEqual((result.created, result.updated, len(result.errors)), (1, 1, 1))
        monitor = Equipment.objects.get(inventory_number="MON-1")
        self.assertEqual(monitor.parent, self.pc)
        self.assertEqual(monitor.assigned_user, self.employee)
        self.pc.refresh_from_db()
        self.assertEqual(self.pc.name, "ПК бухгалтера (обновлено)")
        self.assertEqual(self.pc.installations.count(), 2)

    def test_import_xlsx(self):
        from io import BytesIO

        from openpyxl import Workbook

        from .importers import import_equipment

        workbook = Workbook()
        workbook.active.append(["Инв. номер", "Название", "Категория", "Кабинет", "Статус"])
        workbook.active.append(["MFU-1", "МФУ", "МФУ", "Коридор", "На складе"])
        buffer = BytesIO()
        workbook.save(buffer)
        result = import_equipment("реестр.xlsx", buffer.getvalue())
        self.assertTrue(result.ok)
        self.assertEqual(Equipment.objects.get(inventory_number="MFU-1").status, Equipment.Status.STOCK)

    def test_labels_page_for_registry_roles_only(self):
        manager = User.objects.create_user(username="boss", password="pass")
        Profile.objects.create(user=manager, role=Profile.Role.MANAGER)
        self.client.force_login(manager)
        self.assertContains(self.client.get(reverse("equipment_labels")), "PC-1")
        self.client.force_login(self.employee)
        self.assertEqual(self.client.get(reverse("equipment_labels")).status_code, 302)

    def test_email_sent_to_support_on_new_ticket(self):
        from django.core import mail

        self.engineer.email = "eng@example.com"
        self.engineer.save()
        with self.settings(EMAIL_HOST="smtp.example.com", EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            self.client.force_login(self.employee)
            self.client.post(
                reverse("ticket_create"),
                {"title": "Не включается ПК", "description": "-", "category": self.ticket_category.id, "equipment": self.pc.id, "priority": "high"},
            )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["eng@example.com"])

    def test_login_lockout_after_failures(self):
        for _ in range(5):
            self.client.post(reverse("login"), {"username": "petrova", "password": "wrong"})
        response = self.client.post(reverse("login"), {"username": "petrova", "password": "pass"})
        self.assertEqual(response.status_code, 429)
        self.assertContains(response, "Слишком много неудачных попыток", status_code=429)
