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
