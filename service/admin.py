from django.contrib import admin

from .models import (
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


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "department")
    list_filter = ("role", "department")
    search_fields = ("user__username", "user__first_name", "user__last_name")


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ("name", "inventory_number", "category", "location", "criticality")
    list_filter = ("category", "criticality", "location")
    search_fields = ("name", "inventory_number", "serial_number", "model")


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

# Register your models here.
