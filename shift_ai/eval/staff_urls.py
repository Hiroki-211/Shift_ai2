from django.urls import path
from . import staff_views

app_name = 'staff'

urlpatterns = [
    # スタッフ評価・勤怠機能
    path('evaluation/', staff_views.staff_evaluation_view, name='evaluation_view'),
    path('attendance-records/', staff_views.staff_attendance_records, name='attendance_records'),
    path('attendance/<int:record_id>/', staff_views.staff_attendance_detail, name='attendance_detail'),
    path('attendance/<int:record_id>/delete/', staff_views.staff_attendance_delete, name='attendance_delete'),
]
