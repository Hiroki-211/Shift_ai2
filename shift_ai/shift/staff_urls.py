from django.urls import path
from . import staff_views

app_name = 'staff_shift'

urlpatterns = [
    # スタッフシフト機能
    path('shift-requests/', staff_views.staff_shift_requests, name='shift_requests'),
    path('shift-view/', staff_views.staff_shift_view, name='shift_view'),
    path('shift/<int:shift_id>/', staff_views.staff_shift_detail, name='shift_detail'),
    path('leave-requests/', staff_views.leave_requests, name='leave_requests'),
    path('paid-leave-requests/', staff_views.paid_leave_requests, name='paid_leave_requests'),
]
