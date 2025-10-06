from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from datetime import datetime, date, timedelta
from .models import Shift, ShiftRequest
from accounts.models import Staff


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
def staff_shift_requests(request):
    """スタッフ希望シフト提出"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    # 今月の希望シフトを取得
    today = date.today()
    month_start = today.replace(day=1)
    if today.month == 12:
        month_end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        month_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    
    shift_requests = ShiftRequest.objects.filter(
        staff=staff,
        date__range=[month_start, month_end]
    ).order_by('date')
    
    if request.method == 'POST':
        # 希望シフトの提出
        request_type = request.POST.get('request_type')
        selected_dates = request.POST.getlist('dates')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        
        if not selected_dates:
            messages.error(request, "日付が選択されていません。")
        else:
            created_count = 0
            for date_str in selected_dates:
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                    
                    # 既存の希望を削除
                    ShiftRequest.objects.filter(
                        staff=staff,
                        date=date_obj,
                        request_type=request_type
                    ).delete()
                    
                    # 新しい希望を作成
                    shift_request = ShiftRequest.objects.create(
                        staff=staff,
                        date=date_obj,
                        request_type=request_type,
                        start_time=datetime.strptime(start_time, '%H:%M').time() if start_time else None,
                        end_time=datetime.strptime(end_time, '%H:%M').time() if end_time else None,
                    )
                    created_count += 1
                    
                except ValueError:
                    continue
            
            messages.success(request, f"{created_count}件の希望シフトを提出しました。")
            return redirect('staff_shift:shift_requests')
    
    context = {
        'staff': staff,
        'shift_requests': shift_requests,
        'month_start': month_start,
        'month_end': month_end,
    }
    
    return render(request, 'staff/shift_requests.html', context)


@login_required
@staff_required
def staff_shift_view(request):
    """スタッフシフト確認"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    # 今月のシフトを取得
    today = date.today()
    month_start = today.replace(day=1)
    if today.month == 12:
        month_end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        month_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    
    shifts = Shift.objects.filter(
        staff=staff,
        date__range=[month_start, month_end]
    ).order_by('date', 'start_time')
    
    # 勤務時間集計
    total_hours = sum(shift.duration_hours for shift in shifts.filter(is_confirmed=True))
    
    # スキルレベルのパーセンテージ計算
    hall_skill_percentage = staff.hall_skill_level * 20
    kitchen_skill_percentage = staff.kitchen_skill_level * 20
    
    # 週別シフト表示用
    weekly_shifts = {}
    for shift in shifts:
        week_start = shift.date - timedelta(days=shift.date.weekday())
        if week_start not in weekly_shifts:
            weekly_shifts[week_start] = []
        weekly_shifts[week_start].append(shift)
    
    context = {
        'staff': staff,
        'shifts': shifts,
        'weekly_shifts': weekly_shifts,
        'total_hours': total_hours,
        'hall_skill_percentage': hall_skill_percentage,
        'kitchen_skill_percentage': kitchen_skill_percentage,
        'month_start': month_start,
        'month_end': month_end,
    }
    
    return render(request, 'staff/shift_view.html', context)


@login_required
@staff_required
def staff_shift_detail(request, shift_id):
    """スタッフ用シフト詳細"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    shift = get_object_or_404(Shift, id=shift_id, staff=staff)
    
    context = {
        'shift': shift,
        'staff': staff,
    }
    
    return render(request, 'staff/shift_detail.html', context)
