from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from .models import Store, Staff, StaffRequirement, Announcement


def staff_required(view_func):
    """スタッフ権限が必要なデコレータ"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        try:
            staff = request.user.staff
        except Staff.DoesNotExist:
            messages.error(request, "スタッフ情報が見つかりません。")
            return redirect('login')
        
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@staff_required
def staff_dashboard(request):
    """スタッフダッシュボード"""
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
    
    # 今月のシフトを取得
    monthly_shifts = Shift.objects.filter(
        staff=staff,
        date__range=[month_start, month_end]
    ).order_by('date', 'start_time')
    
    confirmed_shifts = monthly_shifts.filter(is_confirmed=True)
    unconfirmed_shifts = monthly_shifts.filter(is_confirmed=False)
    
    # 勤務時間集計
    total_hours = sum(shift.duration_hours for shift in confirmed_shifts)
    
    # スキルレベルのパーセンテージ計算
    hall_skill_percentage = staff.hall_skill_level * 20
    kitchen_skill_percentage = staff.kitchen_skill_level * 20
    
    # 今月の勤怠記録
    from eval.models import AttendanceRecord
    attendance_records = AttendanceRecord.objects.filter(
        staff=staff,
        date__range=[month_start, month_end]
    ).order_by('-date')[:5]  # 最新5件
    
    # 最新の評価
    from eval.models import Evaluation
    latest_evaluation = Evaluation.objects.filter(staff=staff).order_by('-evaluation_period').first()
    
    context = {
        'staff': staff,
        'store': store,
        'monthly_shifts': monthly_shifts,
        'confirmed_shifts': confirmed_shifts,
        'unconfirmed_shifts': unconfirmed_shifts,
        'total_hours': total_hours,
        'hall_skill_percentage': hall_skill_percentage,
        'kitchen_skill_percentage': kitchen_skill_percentage,
        'attendance_records': attendance_records,
        'latest_evaluation': latest_evaluation,
        'month_start': month_start,
        'month_end': month_end,
    }
    
    return render(request, 'staff/dashboard.html', context)


@login_required
@staff_required
def staff_profile(request):
    """スタッフプロフィール"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    context = {
        'staff': staff,
        'store': store,
    }
    
    return render(request, 'staff/profile.html', context)


@login_required
@staff_required
def staff_announcement_list(request):
    """従業員用お知らせ一覧"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    # 公開中のお知らせのみ取得
    announcements = Announcement.objects.filter(
        store=store,
        is_published=True
    ).order_by('-created_at')
    
    # ページネーション
    paginator = Paginator(announcements, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'staff': staff,
        'store': store,
        'announcements': page_obj,
    }
    return render(request, 'staff/announcement_list.html', context)


@login_required
@staff_required
def staff_announcement_detail(request, announcement_id):
    """従業員用お知らせ詳細"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    announcement = get_object_or_404(
        Announcement,
        id=announcement_id,
        store=store,
        is_published=True
    )
    
    context = {
        'staff': staff,
        'store': store,
        'announcement': announcement,
    }
    return render(request, 'staff/announcement_detail.html', context)
