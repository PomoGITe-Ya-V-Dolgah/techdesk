"""Маршруты проекта. Адрес админки задается в .env (DJANGO_ADMIN_URL)."""

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from service.auth_views import ThrottledLoginView

urlpatterns = [
    path('', include('service.urls')),
    path('login/', ThrottledLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path(settings.ADMIN_URL, admin.site.urls),
]
