from django.urls import path
from . import staff_views

app_name = 'staff'

urlpatterns = [
    # スタッフダッシュボード
    path('', staff_views.staff_dashboard, name='dashboard'),
    
    # プロフィール
    path('profile/', staff_views.staff_profile, name='profile'),
]
