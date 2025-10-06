from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from .models import Store, Staff, StaffRequirement
from .forms import StoreForm, StaffForm, StaffRequirementForm, UserRegistrationForm


@login_required
def dashboard(request):
    """管理者ダッシュボード"""
    # ユーザーがスタッフとして登録されているかチェック
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    # 今月のシフト状況を取得
    from datetime import datetime, date, timedelta
    from shift.models import Shift
    
    today = date.today()
    month_start = today.replace(day=1)
    if today.month == 12:
        month_end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        month_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    
    # 今月のシフト統計
    monthly_shifts = Shift.objects.filter(
        store=store,
        date__range=[month_start, month_end]
    )
    
    total_shifts = monthly_shifts.count()
    confirmed_shifts = monthly_shifts.filter(is_confirmed=True).count()
    unconfirmed_shifts = total_shifts - confirmed_shifts
    
    # 人件費計算
    total_cost = sum(shift.wage_cost for shift in monthly_shifts.filter(is_confirmed=True))
    
    # 確定率計算
    confirmation_rate = (confirmed_shifts / total_shifts * 100) if total_shifts > 0 else 0
    
    context = {
        'store': store,
        'total_shifts': total_shifts,
        'confirmed_shifts': confirmed_shifts,
        'unconfirmed_shifts': unconfirmed_shifts,
        'total_cost': total_cost,
        'confirmation_rate': confirmation_rate,
    }
    
    return render(request, 'accounts/dashboard.html', context)


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
                return redirect('login')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'registration/register.html', {'form': form})
