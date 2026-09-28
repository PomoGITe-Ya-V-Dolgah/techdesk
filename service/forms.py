from django import forms
from django.contrib.auth.models import User

from .models import Equipment, Profile, Software, SoftwareInstallation, Ticket, TicketComment


class StyledFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.Select):
                css_class = "form-select"
            elif isinstance(widget, forms.CheckboxInput):
                css_class = "form-check-input"
            else:
                css_class = "form-control"
            existing = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{existing} {css_class}".strip()


class EquipmentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Equipment
        fields = [
            "name",
            "inventory_number",
            "serial_number",
            "category",
            "location",
            "department",
            "manufacturer",
            "model",
            "criticality",
            "status",
            "assigned_user",
            "parent",
            "hostname",
            "ip_address",
            "mac_address",
            "operating_system",
            "purchase_date",
            "warranty_until",
            "notes",
        ]
        widgets = {
            "purchase_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "warranty_until": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_user"].queryset = User.objects.filter(is_active=True).order_by("last_name", "first_name", "username")
        self.fields["assigned_user"].label_from_instance = lambda user: user.get_full_name() or user.username
        parents = Equipment.objects.exclude(status=Equipment.Status.WRITTEN_OFF)
        if self.instance.pk:
            parents = parents.exclude(pk=self.instance.pk)
        self.fields["parent"].queryset = parents


class SoftwareInstallationForm(StyledFormMixin, forms.Form):
    software = forms.CharField(label="Программа", max_length=160, widget=forms.TextInput(attrs={"list": "software-names"}))
    version = forms.CharField(label="Версия", max_length=60, required=False)
    license_until = forms.DateField(label="Лицензия до", required=False, widget=forms.DateInput(attrs={"type": "date"}))

    def save(self, equipment):
        software, _ = Software.objects.get_or_create(name=self.cleaned_data["software"].strip())
        installation, _ = SoftwareInstallation.objects.update_or_create(
            equipment=equipment,
            software=software,
            defaults={"version": self.cleaned_data["version"], "license_until": self.cleaned_data["license_until"]},
        )
        return installation


class EquipmentImportForm(StyledFormMixin, forms.Form):
    file = forms.FileField(label="Файл Excel (.xlsx) или CSV")

    def clean_file(self):
        file = self.cleaned_data["file"]
        if not file.name.lower().endswith((".xlsx", ".csv")):
            raise forms.ValidationError("Нужен файл .xlsx или .csv.")
        if file.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Файл больше 5 МБ.")
        return file


class TicketForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["title", "description", "category", "equipment", "priority", "due_at"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "due_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, simple=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["equipment"].queryset = Equipment.objects.exclude(status=Equipment.Status.WRITTEN_OFF).select_related("location")
        self.fields["equipment"].label_from_instance = lambda item: f"{item.name} ({item.inventory_number}) — {item.location}"
        if simple:
            # Сотруднику не нужен срок выполнения — его ставит техотдел.
            del self.fields["due_at"]


class TicketAssignForm(StyledFormMixin, forms.ModelForm):
    assignee = forms.ModelChoiceField(
        label="Исполнитель",
        queryset=User.objects.none(),
        required=True,
    )

    class Meta:
        model = Ticket
        fields = ["assignee"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assignee"].queryset = User.objects.filter(profile__role=Profile.Role.ENGINEER).order_by("last_name", "username")


class TicketStatusForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["status", "resolution_summary"]
        widgets = {
            "resolution_summary": forms.Textarea(attrs={"rows": 4}),
        }

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        resolution = cleaned.get("resolution_summary", "").strip()
        if status in {Ticket.Status.RESOLVED, Ticket.Status.CLOSED} and not resolution:
            raise forms.ValidationError("Для выполнения или закрытия заявки необходимо указать итоговое решение.")
        return cleaned


class TicketCommentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = TicketComment
        fields = ["text"]
        widgets = {
            "text": forms.Textarea(attrs={"rows": 3, "placeholder": "Опишите выполненное действие или уточнение"}),
        }
