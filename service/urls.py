from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("equipment/", views.equipment_list, name="equipment_list"),
    path("equipment/create/", views.equipment_create, name="equipment_create"),
    path("equipment/<int:pk>/", views.equipment_detail, name="equipment_detail"),
    path("equipment/<int:pk>/edit/", views.equipment_update, name="equipment_update"),
    path("equipment/<int:pk>/qr/", views.equipment_qr, name="equipment_qr"),
    path("tickets/", views.ticket_list, name="ticket_list"),
    path("tickets/create/", views.ticket_create, name="ticket_create"),
    path("tickets/<int:pk>/", views.ticket_detail, name="ticket_detail"),
    path("tickets/<int:pk>/assign/", views.ticket_assign, name="ticket_assign"),
    path("tickets/<int:pk>/status/", views.ticket_status, name="ticket_status"),
    path("reports/", views.reports, name="reports"),
    path("reports/export.csv", views.reports_export_csv, name="reports_export_csv"),
]
