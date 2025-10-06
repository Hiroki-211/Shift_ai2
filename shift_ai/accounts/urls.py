from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('store-settings/', views.store_settings, name='store_settings'),
    path('staff-management/', views.staff_management, name='staff_management'),
    path('staff/<int:staff_id>/', views.staff_detail, name='staff_detail'),
    path('staff-requirements/', views.staff_requirements, name='staff_requirements'),
    path('staff-requirements/<int:requirement_id>/delete/', views.delete_requirement, name='delete_requirement'),
]
