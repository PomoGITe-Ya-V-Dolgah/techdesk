from django.contrib import admin

from .models import (
    Department,
    Equipment,
    EquipmentCategory,
    Location,
    Profile,
    Software,
    SoftwareInstallation,
    Solution,
    Ticket,
    TicketCategory,
    TicketComment,
)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "department", "position", "phone")
    list_filter = ("role", "department")
    search_fields = ("user__username", "user__first_name", "user__last_name")


class SoftwareInstallationInline(admin.TabularInline):
    model = SoftwareInstallation
    extra = 1
    autocomplete_fields = ("software",)


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ("name", "inventory_number", "category", "location", "assigned_user", "status", "ip_address")
    list_filter = ("status", "category", "criticality", "location")
    search_fields = ("name", "inventory_number", "serial_number", "model", "hostname", "ip_address")
    autocomplete_fields = ("assigned_user", "parent")
    inlines = [SoftwareInstallationInline]


@admin.register(Software)
class SoftwareAdmin(admin.ModelAdmin):
    list_display = ("name", "vendor", "license_type")
    list_filter = ("license_type",)
    search_fields = ("name", "vendor")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "equipment", "status", "priority", "assignee", "created_at")
    list_filter = ("status", "priority", "category", "assignee")
    search_fields = ("title", "description", "equipment__name", "equipment__inventory_number")


admin.site.register(Department)
admin.site.register(Location)
admin.site.register(EquipmentCategory)
admin.site.register(TicketCategory)
admin.site.register(TicketComment)
admin.site.register(Solution)
