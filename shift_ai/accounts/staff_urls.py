from django.urls import path
from . import staff_views

app_name = 'staff_accounts'

urlpatterns = [
    # スタッフダッシュボード
    path('', staff_views.staff_dashboard, name='dashboard'),
    
    # プロフィール
    path('profile/', staff_views.staff_profile, name='profile'),
    
    # お知らせ
    path('announcements/', staff_views.staff_announcement_list, name='announcement_list'),
    path('announcements/<int:announcement_id>/', staff_views.staff_announcement_detail, name='announcement_detail'),
]
