from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from django.views import View
from django.contrib.auth.views import LoginView
from .models import Store, Staff, StaffRequirement
from .forms import StoreForm, StaffForm, StaffRequirementForm, UserRegistrationForm


@never_cache
def home(request):
    """ホームページ（ログイン選択画面）"""
    if request.user.is_authenticated:
        # ログイン済みの場合は適切なダッシュボードにリダイレクト
        try:
            staff = request.user.staff
            if staff.is_manager:
                return redirect('admin_accounts:dashboard')
            else:
                return redirect('staff_accounts:dashboard')
        except Staff.DoesNotExist:
            messages.error(request, "スタッフ情報が見つかりません。")
            return redirect('admin_login')
    response = render(request, 'home.html')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


@login_required
def dashboard(request):
    """ダッシュボード（管理者・スタッフの判定とリダイレクト）"""
    try:
        staff = request.user.staff
        if staff.is_manager:
            return redirect('admin_accounts:dashboard')
        else:
            return redirect('staff_accounts:dashboard')
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('admin_login')


@login_required
def store_settings(request):
    """店舗設定"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    if request.method == 'POST':
        form = StoreForm(request.POST, instance=store)
        if form.is_valid():
            form.save()
            messages.success(request, "店舗設定を更新しました。")
            return redirect('store_settings')
    else:
        form = StoreForm(instance=store)
    
    return render(request, 'accounts/store_settings.html', {'form': form})


@login_required
def staff_management(request):
    """スタッフ管理"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    # 検索機能
    search_query = request.GET.get('search', '')
    staff_list = Staff.objects.filter(store=store)
    
    if search_query:
        staff_list = staff_list.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    # ページネーション
    paginator = Paginator(staff_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'accounts/staff_management.html', context)


@login_required
def staff_detail(request, staff_id):
    """スタッフ詳細・編集"""
    try:
        current_staff = request.user.staff
        store = current_staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    staff = get_object_or_404(Staff, id=staff_id, store=store)
    
    if request.method == 'POST':
        form = StaffForm(request.POST, instance=staff)
        if form.is_valid():
            form.save()
            messages.success(request, "スタッフ情報を更新しました。")
            return redirect('staff_management')
    else:
        form = StaffForm(instance=staff)
    
    return render(request, 'accounts/staff_detail.html', {'form': form, 'staff': staff})


@login_required
def staff_requirements(request):
    """必要人数設定"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    requirements = StaffRequirement.objects.filter(store=store).order_by('day_of_week', 'start_time')
    
    if request.method == 'POST':
        form = StaffRequirementForm(request.POST)
        if form.is_valid():
            requirement = form.save(commit=False)
            requirement.store = store
            requirement.save()
            messages.success(request, "必要人数設定を追加しました。")
            return redirect('staff_requirements')
    else:
        form = StaffRequirementForm()
    
    context = {
        'requirements': requirements,
        'form': form,
    }
    
    return render(request, 'accounts/staff_requirements.html', context)


@login_required
def delete_requirement(request, requirement_id):
    """必要人数設定削除"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    requirement = get_object_or_404(StaffRequirement, id=requirement_id, store=store)
    
    if request.method == 'POST':
        requirement.delete()
        messages.success(request, "必要人数設定を削除しました。")
    
    return redirect('staff_requirements')


class AdminLoginView(LoginView):
    """管理者用ログインビュー"""
    template_name = 'registration/admin_login.html'
    
    def dispatch(self, *args, **kwargs):
        """キャッシュを無効化"""
        response = super().dispatch(*args, **kwargs)
        # すべてのレスポンスにキャッシュ無効化ヘッダーを設定
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
    
    def form_valid(self, form):
        """ログイン成功時の処理"""
        user = form.get_user()
        
        # スタッフ情報を確認
        try:
            staff = user.staff
            if not staff.is_manager:
                messages.error(self.request, "このアカウントは管理者権限がありません。スタッフログインをご利用ください。")
                return self.form_invalid(form)
        except Staff.DoesNotExist:
            messages.error(self.request, "スタッフ情報が見つかりません。")
            return self.form_invalid(form)
        
        return super().form_valid(form)
    
    def get_success_url(self):
        """ログイン成功時のリダイレクト先"""
        return '/admin-panel/'


class StaffLoginView(LoginView):
    """スタッフ用ログインビュー"""
    template_name = 'registration/staff_login.html'
    
    def dispatch(self, *args, **kwargs):
        """キャッシュを無効化"""
        response = super().dispatch(*args, **kwargs)
        # すべてのレスポンスにキャッシュ無効化ヘッダーを設定
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
    
    def form_valid(self, form):
        """ログイン成功時の処理"""
        user = form.get_user()
        
        # スタッフ情報を確認
        try:
            staff = user.staff
            if staff.is_manager:
                messages.error(self.request, "このアカウントは管理者アカウントです。管理者ログインをご利用ください。")
                return self.form_invalid(form)
        except Staff.DoesNotExist:
            messages.error(self.request, "スタッフ情報が見つかりません。")
            return self.form_invalid(form)
        
        return super().form_valid(form)
    
    def get_success_url(self):
        """ログイン成功時のリダイレクト先"""
        return '/staff/'


def register(request):
    """ユーザー登録"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save()
                
                # デフォルトの店舗を作成（最初のユーザーの場合）
                store, created = Store.objects.get_or_create(
                    name="デフォルト店舗",
                    defaults={
                        'opening_time': '09:00',
                        'closing_time': '22:00',
                        'preparation_minutes': 60,
                        'cleanup_minutes': 60,
                    }
                )
                
                # スタッフ情報を作成
                Staff.objects.create(
                    user=user,
                    store=store,
                    employment_type='fixed',
                    hourly_wage=1000,
                    is_manager=True,  # 最初のユーザーは管理者
                )
                
                messages.success(request, "アカウントが作成されました。ログインしてください。")
                return redirect('admin_login')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'registration/register.html', {'form': form})


@never_cache
def custom_logout(request):
    """カスタムログアウトビュー（キャッシュを無効化）"""
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, "ログアウトしました。")
    
    # キャッシュを無効化するヘッダーを設定
    response = redirect('home')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response
