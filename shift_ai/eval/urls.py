from django.urls import path
from . import views

app_name = 'eval'

urlpatterns = [
    path('evaluation-input/', views.evaluation_input, name='evaluation_input'),
    path('evaluation/<int:evaluation_id>/', views.evaluation_detail, name='evaluation_detail'),
    path('staff-evaluation/', views.staff_evaluation_view, name='staff_evaluation_view'),
    path('attendance-records/', views.attendance_records, name='attendance_records'),
    path('attendance/<int:record_id>/', views.attendance_detail, name='attendance_detail'),
    path('evaluation-reports/', views.evaluation_reports, name='evaluation_reports'),
]
