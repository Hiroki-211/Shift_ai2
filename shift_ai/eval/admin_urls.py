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
]
