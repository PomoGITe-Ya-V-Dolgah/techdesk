from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("locations/", views.locations_overview, name="locations_overview"),
    path("equipment/", views.equipment_list, name="equipment_list"),
    path("equipment/create/", views.equipment_create, name="equipment_create"),
    path("equipment/import/", views.equipment_import, name="equipment_import"),
    path("equipment/import/template.csv", views.equipment_import_template, name="equipment_import_template"),
    path("equipment/export.csv", views.equipment_export_csv, name="equipment_export_csv"),
    path("equipment/labels/", views.equipment_labels, name="equipment_labels"),
    path("equipment/<int:pk>/", views.equipment_detail, name="equipment_detail"),
    path("equipment/<int:pk>/edit/", views.equipment_update, name="equipment_update"),
    path("equipment/<int:pk>/qr/", views.equipment_qr, name="equipment_qr"),
    path("equipment/<int:pk>/software/add/", views.equipment_software_add, name="equipment_software_add"),
    path("equipment/<int:pk>/software/<int:installation_pk>/remove/", views.equipment_software_remove, name="equipment_software_remove"),
    path("tickets/", views.ticket_list, name="ticket_list"),
    path("tickets/create/", views.ticket_create, name="ticket_create"),
    path("tickets/<int:pk>/", views.ticket_detail, name="ticket_detail"),
    path("tickets/<int:pk>/assign/", views.ticket_assign, name="ticket_assign"),
    path("tickets/<int:pk>/status/", views.ticket_status, name="ticket_status"),
    path("reports/", views.reports, name="reports"),
    path("reports/export.csv", views.reports_export_csv, name="reports_export_csv"),
]
