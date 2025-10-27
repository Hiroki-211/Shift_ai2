from django.urls import path
from . import admin_views

app_name = 'admin_shift'

urlpatterns = [
    # シフト管理
    path('shift-creation/', admin_views.admin_shift_creation, name='shift_creation'),
    path('shift-calendar/', admin_views.admin_shift_calendar, name='shift_calendar'),
    path('submission-status/', admin_views.admin_shift_submission_status, name='submission_status'),
    path('generate-ai/', admin_views.admin_generate_ai_shifts, name='generate_ai_shifts'),
    path('shift/<int:shift_id>/', admin_views.admin_shift_detail, name='shift_detail'),
    path('shift/<int:shift_id>/delete/', admin_views.admin_delete_shift, name='delete_shift'),
    path('confirm-shifts/', admin_views.admin_confirm_shifts, name='confirm_shifts'),
    path('staff-requests/', admin_views.admin_staff_shift_requests, name='staff_shift_requests'),
    path('api/submission-detail/<int:staff_id>/', admin_views.admin_submission_detail_api, name='submission_detail_api'),
]
