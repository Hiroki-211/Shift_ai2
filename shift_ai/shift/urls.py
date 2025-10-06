from django.urls import path
from . import views

app_name = 'shift'

urlpatterns = [
    path('', views.shift_creation, name='shift_creation'),
    path('generate-ai/', views.generate_ai_shifts, name='generate_ai_shifts'),
    path('shift/<int:shift_id>/', views.shift_detail, name='shift_detail'),
    path('shift/<int:shift_id>/delete/', views.delete_shift, name='delete_shift'),
    path('confirm-shifts/', views.confirm_shifts, name='confirm_shifts'),
    path('staff-requests/', views.staff_shift_requests, name='staff_shift_requests'),
    path('staff-view/', views.staff_shift_view, name='staff_shift_view'),
]
