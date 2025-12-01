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
    path('create-from-requests/', admin_views.admin_create_shifts_from_requests, name='create_from_requests'),
    path('staff-requests/', admin_views.admin_staff_shift_requests, name='staff_shift_requests'),
    path('shift-settings/', admin_views.admin_shift_settings, name='shift_settings'),
    path('api/submission-detail/<int:staff_id>/', admin_views.admin_submission_detail_api, name='submission_detail_api'),
    path('api/shift-detail-by-date/<str:shift_date>/', admin_views.admin_shift_detail_by_date, name='shift_detail_by_date'),
    # チャット機能
    path('chat/', admin_views.admin_chat_list, name='chat_list'),
    path('chat/<int:room_id>/', admin_views.admin_chat_detail, name='chat_detail'),
    path('chat/create/<int:staff_id>/', admin_views.admin_chat_create, name='chat_create'),
]
