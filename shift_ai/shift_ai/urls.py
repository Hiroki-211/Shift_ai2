"""
URL configuration for shift_ai project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from accounts import views as accounts_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 認証関連
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', accounts_views.register, name='register'),
    
    # 管理者画面
    path('admin-panel/', include('accounts.admin_urls')),
    path('admin-panel/shift/', include('shift.admin_urls')),
    path('admin-panel/eval/', include('eval.admin_urls')),
    
    # スタッフ画面
    path('staff/', include('accounts.staff_urls')),
    path('staff/shift/', include('shift.staff_urls')),
    path('staff/eval/', include('eval.staff_urls')),
    
    # リダイレクト用（既存のURLとの互換性のため）
    path('', accounts_views.dashboard, name='dashboard'),
    path('shift/', include('shift.urls')),
    path('eval/', include('eval.urls')),
]
