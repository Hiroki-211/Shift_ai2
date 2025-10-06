from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
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
    
    # カレンダー用の週データを生成
    calendar_weeks = generate_calendar_weeks(month_start, month_end)
    
    context = {
        'staff': staff,
        'shift_requests': shift_requests,
        'month_start': month_start,
        'month_end': month_end,
        'calendar_weeks': calendar_weeks,
    }
    
    return render(request, 'staff/shift_requests.html', context)


def generate_calendar_weeks(month_start, month_end):
    """カレンダー用の週データを生成"""
    # 月の最初の日を取得
    first_day = month_start
    
    # その月の最初の週の日曜日を取得
    # weekday(): 0=月曜日, 1=火曜日, ..., 6=日曜日
    days_since_sunday = (first_day.weekday() + 1) % 7  # 日曜日を0にする
    calendar_start = first_day - timedelta(days=days_since_sunday)
    
    # 6週分のデータを生成（42日）
    weeks = []
    current_date = calendar_start
    
    for week_num in range(6):
        week = []
        for day_num in range(7):
            is_current_month = current_date.month == month_start.month
            week.append({
                'date': current_date,
                'is_current_month': is_current_month
            })
            current_date += timedelta(days=1)
        weeks.append(week)
    
    return weeks


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
    
    # 今月の日付範囲を取得
    today = date.today()
    month_start = today.replace(day=1)
    if today.month == 12:
        month_end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        month_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    
    # 今月のシフトを取得
    shifts = Shift.objects.filter(
        staff=staff,
        date__range=[month_start, month_end]
    ).order_by('date', 'start_time')
    
    # 今月の全日付のリストを作成
    monthly_shifts = []
    current_date = month_start
    while current_date <= month_end:
        # 該当日のシフトを検索
        day_shift = next(
            (shift for shift in shifts if shift.date == current_date), 
            None
        )
        
        monthly_shifts.append({
            'date': current_date,
            'shift': day_shift
        })
        
        current_date += timedelta(days=1)
    
    # シフト数の集計
    shift_count = len([day for day in monthly_shifts if day['shift']])
    confirmed_shift_count = len([day for day in monthly_shifts if day['shift'] and day['shift'].is_confirmed])
    
    context = {
        'staff': staff,
        'shifts': shifts,  # 既存のコードとの互換性のため
        'monthly_shifts': monthly_shifts,
        'shift_count': shift_count,
        'confirmed_shift_count': confirmed_shift_count,
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


@login_required
@staff_required
def leave_requests(request):
    """希望休提出（固定契約者のみ）"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    # 固定契約者かどうかをチェック
    if not staff.is_contract_employee:
        messages.warning(request, "希望休提出は固定契約者のみ利用可能です。")
        return redirect('staff_accounts:dashboard')
    
    if request.method == 'POST':
        # 希望休提出の処理
        leave_date = request.POST.get('leave_date')
        reason = request.POST.get('reason', '')
        
        if leave_date:
            try:
                leave_date = datetime.strptime(leave_date, '%Y-%m-%d').date()
                # 希望休申請の保存処理（モデルが必要）
                messages.success(request, f"{leave_date}の希望休を申請しました。")
                return redirect('staff_shift:leave_requests')
            except ValueError:
                messages.error(request, "正しい日付を入力してください。")
        else:
            messages.error(request, "希望休の日付を選択してください。")
    
    # 今月と来月の希望休申請一覧を取得
    today = timezone.now().date()
    current_month = today.replace(day=1)
    next_month = (current_month + timedelta(days=32)).replace(day=1)
    
    context = {
        'staff': staff,
        'current_month': current_month,
        'next_month': next_month,
    }
    
    return render(request, 'staff/leave_requests.html', context)


@login_required
@staff_required
def paid_leave_requests(request):
    """有給提出"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    if request.method == 'POST':
        # 有給申請の処理
        leave_date = request.POST.get('leave_date')
        reason = request.POST.get('reason', '')
        
        if leave_date:
            try:
                leave_date = datetime.strptime(leave_date, '%Y-%m-%d').date()
                # 有給申請の保存処理（モデルが必要）
                messages.success(request, f"{leave_date}の有給申請を提出しました。")
                return redirect('staff_shift:paid_leave_requests')
            except ValueError:
                messages.error(request, "正しい日付を入力してください。")
        else:
            messages.error(request, "有給の日付を選択してください。")
    
    # 有給残日数の計算（仮の実装）
    remaining_paid_leave = 10  # 実際はデータベースから計算
    
    context = {
        'staff': staff,
        'remaining_paid_leave': remaining_paid_leave,
    }
    
    return render(request, 'staff/paid_leave_requests.html', context)
