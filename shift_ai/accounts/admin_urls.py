from django.urls import path
from . import admin_views

app_name = 'admin_accounts'

urlpatterns = [
    # 管理者ダッシュボード
    path('', admin_views.admin_dashboard, name='dashboard'),
    
    # 店舗管理
    path('store-settings/', admin_views.admin_store_settings, name='store_settings'),
    
    # スタッフ管理
    path('staff-management/', admin_views.admin_staff_management, name='staff_management'),
    path('staff-register/', admin_views.admin_staff_register, name='staff_register'),
    path('staff/<int:staff_id>/', admin_views.admin_staff_detail, name='staff_detail'),
    path('staff-requirements/', admin_views.admin_staff_requirements, name='staff_requirements'),
    path('staff-requirements/<int:requirement_id>/delete/', admin_views.admin_delete_requirement, name='delete_requirement'),
    
    # お知らせ管理
    path('announcements/', admin_views.admin_announcement_list, name='announcement_list'),
    path('announcements/create/', admin_views.admin_announcement_create, name='announcement_create'),
    path('announcements/<int:announcement_id>/edit/', admin_views.admin_announcement_edit, name='announcement_edit'),
    path('announcements/<int:announcement_id>/delete/', admin_views.admin_announcement_delete, name='announcement_delete'),
]
