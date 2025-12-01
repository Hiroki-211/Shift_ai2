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
    
    # シフト交代
    path('shift-swap/', staff_views.shift_swap_list, name='shift_swap_list'),
    path('shift-swap/create/', staff_views.shift_swap_create, name='shift_swap_create'),
    path('shift-swap/<int:swap_request_id>/apply/', staff_views.shift_swap_apply, name='shift_swap_apply'),
    path('shift-swap/my-requests/', staff_views.shift_swap_my_requests, name='shift_swap_my_requests'),
    path('shift-swap/<int:swap_request_id>/cancel/', staff_views.shift_swap_cancel, name='shift_swap_cancel'),
    
    # チャット機能
    path('chat/', staff_views.chat_list, name='chat_list'),
    path('chat/<int:room_id>/', staff_views.chat_detail, name='chat_detail'),
    path('chat/create/<int:staff_id>/', staff_views.chat_create, name='chat_create'),
]
