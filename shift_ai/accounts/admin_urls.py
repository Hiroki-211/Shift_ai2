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
    path('staff/<int:staff_id>/', admin_views.admin_staff_detail, name='staff_detail'),
    path('staff-requirements/', admin_views.admin_staff_requirements, name='staff_requirements'),
    path('staff-requirements/<int:requirement_id>/delete/', admin_views.admin_delete_requirement, name='delete_requirement'),
]
