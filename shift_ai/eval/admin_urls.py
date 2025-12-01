from django.urls import path
from . import admin_views

app_name = 'admin_eval'

urlpatterns = [
    # 評価管理
    path('evaluation-input/', admin_views.admin_evaluation_input, name='evaluation_input'),
    path('evaluation/<int:evaluation_id>/', admin_views.admin_evaluation_detail, name='evaluation_detail'),
    path('attendance-records/', admin_views.admin_attendance_records, name='attendance_records'),
    path('attendance/<int:record_id>/', admin_views.admin_attendance_detail, name='attendance_detail'),
    path('evaluation-reports/', admin_views.admin_evaluation_reports, name='evaluation_reports'),
    # 評価項目管理
    path('evaluation-items/', admin_views.admin_evaluation_items, name='evaluation_items'),
    path('evaluation-items/create/', admin_views.admin_evaluation_item_create, name='evaluation_item_create'),
    path('evaluation-items/<int:item_id>/edit/', admin_views.admin_evaluation_item_edit, name='evaluation_item_edit'),
    path('evaluation-items/<int:item_id>/delete/', admin_views.admin_evaluation_item_delete, name='evaluation_item_delete'),
]
