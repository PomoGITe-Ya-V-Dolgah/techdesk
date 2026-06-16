from django import forms
from django.contrib.auth.models import User

from .models import Equipment, Profile, Ticket, TicketComment


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
            "notes",
        ]


class TicketForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["title", "description", "category", "equipment", "priority", "due_at"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "due_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


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
