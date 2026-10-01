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


class TicketLiveTests(TestCase):
    def setUp(self):
        from .models import TicketEvent
        self.Event = TicketEvent
        self.admin = User.objects.create_superuser('root', 'root@example.com', 'pass')
        self.engineer = User.objects.create_user('executor')
        Profile.objects.create(user=self.engineer, role=Profile.Role.ENGINEER)
        self.employee = User.objects.create_user('employee')
        self.other = User.objects.create_user('other')
        self.category = TicketCategory.objects.create(name='Поддержка')
        self.ticket = Ticket.objects.create(title='Тестовая заявка', description='-', category=self.category, reporter=self.employee)

    def event(self, kind='created', **kwargs):
        return self.Event.objects.create(ticket=self.ticket, kind=kind, actor=self.other, **kwargs)

    def test_executor_roles_and_active_users(self):
        from .forms import TicketAssignForm
        administrator = User.objects.create_user('administrator')
        Profile.objects.create(user=administrator, role=Profile.Role.ADMIN)
        inactive = User.objects.create_user('inactive', is_active=False)
        Profile.objects.create(user=inactive, role=Profile.Role.ENGINEER)
        form = TicketAssignForm()
        self.assertSetEqual(set(form.fields['assignee'].queryset), {self.admin, administrator, self.engineer})
        self.assertIn('Администратор', form.fields['assignee'].label_from_instance(self.admin))
        invalid = TicketAssignForm({'assignee': self.employee.pk}, instance=self.ticket)
        self.assertFalse(invalid.is_valid())

    def test_assignment_deadline_and_event(self):
        self.client.force_login(self.admin)
        data = {'assignee': self.engineer.pk, 'due_at': '2026-10-10T15:30'}
        self.assertEqual(self.client.post(reverse('ticket_assign', args=[self.ticket.pk]), data).status_code, 302)
        self.ticket.refresh_from_db()
        from django.utils import timezone
        self.assertEqual(timezone.localtime(self.ticket.due_at).strftime('%Y-%m-%dT%H:%M'), data['due_at'])
        event = self.Event.objects.get()
        self.assertEqual((event.kind, event.recipient_id), ('assigned', self.engineer.pk))
        data['due_at'] = '2026-10-11T16:00'
        self.client.post(reverse('ticket_assign', args=[self.ticket.pk]), data)
        self.assertEqual(self.Event.objects.count(), 1)
        self.assertContains(self.client.get(reverse('ticket_assign', args=[self.ticket.pk])), '2026-10-11T16:00')

    def test_employee_cannot_assign(self):
        self.client.force_login(self.employee)
        self.client.post(reverse('ticket_assign', args=[self.ticket.pk]), {'assignee': self.admin.pk})
        self.ticket.refresh_from_db()
        self.assertIsNone(self.ticket.assignee)
        self.assertFalse(self.Event.objects.exists())

    def test_creation_records_event(self):
        self.client.force_login(self.employee)
        self.client.post(reverse('ticket_create'), {'title': 'Новая', 'description': '-', 'category': self.category.pk, 'priority': 'normal'})
        self.assertEqual(self.Event.objects.get().kind, 'created')

    def test_deadline_status_and_partial_filters(self):
        from datetime import timedelta
        from django.utils import timezone
        self.ticket.due_at = timezone.now() - timedelta(hours=2)
        self.ticket.save()
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse('ticket_detail', args=[self.ticket.pk])), 'Просрочено на')
        response = self.client.get(reverse('ticket_list'), {'partial': '1', 'status': 'closed'})
        self.assertNotContains(response, self.ticket.title)
        self.assertNotContains(response, '<html')
        self.assertEqual(response['Cache-Control'], 'no-store')
        response = self.client.get(reverse('ticket_status', args=[self.ticket.pk]))
        self.assertContains(response, 'type="radio"', count=len(Ticket.Status.choices))
        for value, _ in Ticket.Status.choices:
            self.assertContains(response, f'status-{value}')

    def test_superuser_without_profile_opens_ui(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse('ticket_list')), 'notification-controls')

    def test_events_baseline_and_cursor_validation(self):
        event = self.event()
        self.client.force_login(self.engineer)
        self.assertEqual(self.client.get(reverse('ticket_events')).json(), {'cursor': event.id, 'events': []})
        for cursor in ['bad', '-1', str(event.id+1)]:
            self.assertEqual(self.client.get(reverse('ticket_events'), {'after': cursor}).status_code, 400)

    def test_events_scope_self_and_visibility(self):
        assigned = self.event('assigned', recipient=self.engineer)
        created = self.event()
        self.Event.objects.create(ticket=self.ticket, kind='created', actor=self.engineer)
        self.client.force_login(self.engineer)
        result = self.client.get(reverse('ticket_events'), {'after': 0}).json()
        self.assertEqual([e['id'] for e in result['events']], [assigned.id])
        self.engineer.profile.notification_scope = 'all'
        self.engineer.profile.save()
        result = self.client.get(reverse('ticket_events'), {'after': 0}).json()
        self.assertEqual([e['id'] for e in result['events']], [assigned.id, created.id])
        self.event('assigned', recipient=self.other)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse('ticket_events'), {'after': 0}).json()['events'], [])

    def test_event_pagination_without_loss(self):
        self.Event.objects.bulk_create([self.Event(ticket=self.ticket, kind='assigned', actor=self.other, recipient=self.engineer) for _ in range(105)])
        self.client.force_login(self.engineer)
        first = self.client.get(reverse('ticket_events'), {'after': 0}).json()
        second = self.client.get(reverse('ticket_events'), {'after': first['cursor']}).json()
        self.assertEqual((len(first['events']), len(second['events'])), (100, 5))
        self.assertGreater(second['cursor'], first['cursor'])

    def test_preferences_persist_and_validate_roles(self):
        import json
        url = reverse('notification_preferences')
        self.client.force_login(self.engineer)
        self.assertEqual(self.client.post(url, json.dumps({'sound': True, 'scope': 'all'}), content_type='application/json').status_code, 200)
        self.engineer.profile.refresh_from_db()
        self.assertTrue(self.engineer.profile.notification_sound)
        self.assertEqual(self.engineer.profile.notification_scope, 'all')
        for payload in ['[]', '{', '{"sound":"yes","scope":"all"}']:
            self.assertEqual(self.client.post(url, payload, content_type='application/json').status_code, 400)
        self.client.force_login(self.employee)
        self.assertEqual(self.client.post(url, json.dumps({'sound': True, 'scope': 'all'}), content_type='application/json').status_code, 403)
        from django.test import Client
        secure = Client(enforce_csrf_checks=True)
        secure.force_login(self.engineer)
        self.assertEqual(secure.post(url, json.dumps({'sound': True, 'scope': 'assigned'}), content_type='application/json').status_code, 403)

    def test_anonymous_events_require_login(self):
        self.assertEqual(self.client.get(reverse('ticket_events')).status_code, 302)


class EquipmentRegistryFilterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('viewer')
        self.owner = User.objects.create_user('owner', first_name='Анна', last_name='Петрова')
        self.former = User.objects.create_user('former', is_active=False)
        self.category = EquipmentCategory.objects.create(name='ПК')
        self.location = Location.objects.create(name='Офис')
        self.first = Equipment.objects.create(name='Альфа', inventory_number='02', category=self.category, location=self.location, assigned_user=self.owner, status='repair')
        self.last = Equipment.objects.create(name='Янтарь', inventory_number='01', category=self.category, location=self.location)
        self.old = Equipment.objects.create(name='Бета', inventory_number='03', category=self.category, location=self.location, assigned_user=self.former)
        self.client.force_login(self.user)

    def get(self, **query):
        return self.client.get(reverse('equipment_list'), query)

    def test_employee_and_unassigned_filters(self):
        response = self.get(employee=str(self.owner.pk))
        self.assertEqual(list(response.context['equipment']), [self.first])
        self.assertContains(response, 'Анна Петрова')
        self.assertEqual(list(self.get(employee='unassigned').context['equipment']), [self.last])
        self.assertEqual(list(self.get(employee='bad').context['equipment']), [])
        self.assertIn(self.former, self.get().context['employees'])

    def test_filters_combine(self):
        self.assertEqual(list(self.get(employee=self.owner.pk, category=self.category.pk, location=self.location.pk, status='repair', q='Альфа').context['equipment']), [self.first])
        self.assertEqual(list(self.get(employee=self.owner.pk, status='stock').context['equipment']), [])

    def test_sorting_both_directions_and_allowlist(self):
        self.assertEqual(list(self.get(sort='inventory').context['equipment']), [self.last, self.first, self.old])
        self.assertEqual(list(self.get(sort='-inventory').context['equipment']), [self.old, self.first, self.last])
        self.assertEqual(self.get(sort='assigned_user__password').context['sort'], 'name')
        self.assertEqual(self.get(sort='ip').context['sort'], 'name')
        for key in ['name', 'inventory', 'category', 'location', 'employee', 'status']:
            self.assertEqual(self.get(sort=key).status_code, 200)
            self.assertEqual(self.get(sort='-'+key).status_code, 200)

    def test_sort_links_keep_filters_and_form_keeps_sort(self):
        response = self.get(employee=self.owner.pk, status='repair', sort='inventory', q='Альфа')
        self.assertContains(response, 'name="sort" value="inventory"')
        from html import unescape
        from urllib.parse import parse_qs, urlsplit
        import re
        links = re.findall(r'href="([^\"]+)"', response.content.decode())
        next_link = next(link for link in links if 'sort=-inventory' in link)
        query = parse_qs(urlsplit(unescape(next_link)).query)
        self.assertEqual(query['employee'], [str(self.owner.pk)])
        self.assertEqual(query['status'], ['repair'])
        self.assertEqual(query['q'], ['Альфа'])
        self.assertContains(response, 'aria-sort="ascending"')

    def test_employee_sort_unassigned_last_and_admin_columns(self):
        for key in ['employee', '-employee']:
            self.assertEqual(list(self.get(sort=key).context['equipment'])[-1], self.last)
        Profile.objects.update_or_create(user=self.user, defaults={"role": Profile.Role.ADMIN})
        for key in ['hostname', 'ip']:
            self.assertEqual(self.get(sort=key).context['sort'], key)
        self.assertContains(self.get(), 'Имя ПК')


class TableSortingTests(TestCase):
    def setUp(self):
        from datetime import timedelta
        from django.utils import timezone
        self.user = User.objects.create_user('sortadmin')
        Profile.objects.create(user=self.user, role=Profile.Role.ADMIN)
        category = TicketCategory.objects.create(name='Тест')
        self.first = Ticket.objects.create(title='Альфа', description='-', category=category, reporter=self.user, priority='low', due_at=timezone.now()+timedelta(days=1))
        self.last = Ticket.objects.create(title='Янтарь', description='-', category=category, reporter=self.user, priority='urgent')
        self.client.force_login(self.user)

    def test_queue_sort_and_live_partial_keep_order(self):
        for partial in ['', '1']:
            response = self.client.get(reverse('ticket_list'), {'sort': '-title', 'partial': partial, 'status': 'new'})
            self.assertEqual(list(response.context['tickets']), [self.last, self.first])
            self.assertContains(response, 'sort=title')
            self.assertNotContains(response, 'partial=1')
        response = self.client.get(reverse('ticket_list'), {'sort': 'due'})
        self.assertEqual(list(response.context['tickets']), [self.first, self.last])
        response = self.client.get(reverse('ticket_list'), {'sort': '-due'})
        self.assertEqual(list(response.context['tickets']), [self.first, self.last])
        self.assertEqual(self.client.get(reverse('ticket_list'), {'sort': 'reporter__password'}).context['sort'], '-created')

    def test_priority_sort_and_filter_form(self):
        response = self.client.get(reverse('ticket_list'), {'sort': '-priority'})
        self.assertEqual(list(response.context['tickets']), [self.last, self.first])
        self.assertContains(response, 'name="sort" value="-priority"')
        self.assertContains(response, 'aria-sort="descending"')

    def test_small_tables_have_independent_sort_keys(self):
        self.assertContains(self.client.get(reverse('dashboard')), 'data-sort-table="recent"')
        response = self.client.get(reverse('reports'))
        for key in ['statuses', 'equipment', 'engineers']:
            self.assertContains(response, f'data-sort-table="{key}"')
        category = EquipmentCategory.objects.create(name='ПК')
        equipment = Equipment.objects.create(name='ПК', inventory_number='SORT-1', category=category, location=Location.objects.create(name='Офис'))
        response = self.client.get(reverse('equipment_detail', args=[equipment.pk]))
        for key in ['software', 'history']:
            self.assertContains(response, f'data-sort-table="{key}"')


class MobileFormsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('mobileoperator')
        Profile.objects.create(user=self.user, role=Profile.Role.OPERATOR)
        self.client.force_login(self.user)

    def test_mobile_sort_form_preserves_applied_filters(self):
        from html.parser import HTMLParser

        class SortParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.active = False
                self.fields = {}
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == 'form':
                    self.active = 'mobile-sort' in attrs.get('class', '')
                if self.active and tag == 'input' and attrs.get('type') == 'hidden':
                    self.fields[attrs['name']] = attrs['value']
            def handle_endtag(self, tag):
                if tag == 'form': self.active = False

        for route, query in [('equipment_list', {'employee':'unassigned','status':'repair','q':'ПК & монитор','sort':'-inventory'}), ('ticket_list', {'status':'new','q':'Сеть & доступы','sort':'-due'})]:
            response = self.client.get(reverse(route), query)
            self.assertEqual(response.status_code, 200)
            parser = SortParser()
            parser.feed(response.content.decode())
            self.assertEqual(parser.fields, {k:v for k,v in query.items() if k != 'sort'})
            self.assertContains(response, f'value="{query["sort"]}" selected')

    def test_description_has_full_width_field(self):
        response = self.client.get(reverse('ticket_create'))
        from html.parser import HTMLParser

        class DescriptionParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.wide = False
                self.classes = ''
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == 'div' and 'form-field' in attrs.get('class',''):
                    self.classes = attrs['class']
                if tag == 'textarea' and attrs.get('name') == 'description':
                    self.wide = 'form-field-wide' in self.classes
        parser = DescriptionParser()
        parser.feed(response.content.decode())
        self.assertTrue(parser.wide)
