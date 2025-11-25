from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, date, timedelta
from .models import Shift, ShiftRequest, ShiftSwapRequest, ShiftSwapApplication
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
    
    # 来月の希望シフトを取得
    today = date.today()
    if today.month == 12:
        next_month_start = date(today.year + 1, 1, 1)
    else:
        next_month_start = date(today.year, today.month + 1, 1)
    
    if next_month_start.month == 12:
        next_month_end = date(next_month_start.year + 1, 1, 1) - timedelta(days=1)
    else:
        next_month_end = date(next_month_start.year, next_month_start.month + 1, 1) - timedelta(days=1)
    
    # 提出済みシフトを取得
    shift_requests = ShiftRequest.objects.filter(
        staff=staff,
        date__range=[next_month_start, next_month_end]
    ).order_by('date')
    
    # 提出期限と提出開始日の設定
    # 例：11月のシフトの提出期限は10月の設定日
    store = staff.store
    
    # 提出開始日（前月の設定日）
    if next_month_start.month == 1:
        # 来月が1月の場合、前月（今月）は12月
        submission_start = date(today.year, 12, store.shift_submission_start_day)
        submission_deadline = date(today.year, 12, store.shift_submission_deadline_day)
    else:
        submission_start = date(today.year, today.month, store.shift_submission_start_day)
        submission_deadline = date(today.year, today.month, store.shift_submission_deadline_day)
    
    # 提出可能期間かどうか
    can_edit = submission_start <= today <= submission_deadline
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_existing':
            # 編集モード：既存シフトの削除と更新
            delete_dates = request.POST.getlist('delete_dates')
            update_dates = request.POST.getlist('update_dates')
            request_types = request.POST.getlist('request_types')
            start_times = request.POST.getlist('start_times')
            end_times = request.POST.getlist('end_times')
            
            deleted_count = 0
            updated_count = 0
            
            # 削除処理
            for date_str in delete_dates:
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                    ShiftRequest.objects.filter(
                        staff=staff,
                        date=date_obj
                    ).delete()
                    deleted_count += 1
                except ValueError:
                    continue
            
            # 更新処理
            end_date_offsets = request.POST.getlist('end_date_offsets')
            for i, date_str in enumerate(update_dates):
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                    request_type = request_types[i] if i < len(request_types) else 'work'
                    start_time = start_times[i] if i < len(start_times) and start_times[i] else None
                    end_time = end_times[i] if i < len(end_times) and end_times[i] else None
                    end_date_offset = int(end_date_offsets[i]) if i < len(end_date_offsets) else 0
                    
                    # 終了日の計算
                    end_date = date_obj + timedelta(days=end_date_offset) if end_date_offset > 0 else None
                    
                    # 既存のレコードを削除（重複防止）
                    ShiftRequest.objects.filter(
                        staff=staff,
                        date=date_obj
                    ).delete()
                    
                    # 新しい希望を作成
                    ShiftRequest.objects.create(
                        staff=staff,
                        date=date_obj,
                        request_type=request_type,
                        start_time=datetime.strptime(start_time, '%H:%M').time() if start_time else None,
                        end_time=datetime.strptime(end_time, '%H:%M').time() if end_time else None,
                        end_date=end_date,
                    )
                    updated_count += 1
                    
                except ValueError:
                    continue
            
            messages.success(request, f"{deleted_count}件を削除、{updated_count}件を更新しました。")
            return redirect('staff_shift:shift_requests')
        
        else:
            # 通常モード：新規提出
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
    calendar_weeks = generate_calendar_weeks(next_month_start, next_month_end)
    
    # 提出済みシフトを日付で辞書化（カレンダー表示用）
    submitted_shifts = {}
    for req in shift_requests:
        submitted_shifts[req.date] = req
    
    context = {
        'staff': staff,
        'shift_requests': shift_requests,
        'month_start': next_month_start,
        'month_end': next_month_end,
        'calendar_weeks': calendar_weeks,
        'submitted_shifts': submitted_shifts,
        'can_edit': can_edit,
        'today': today,
        'submission_start': submission_start,
        'submission_deadline': submission_deadline,
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
    
    # カレンダーの最後の日を計算（月の最後の日以降の土曜日）
    last_sunday_of_month = month_end + timedelta(days=(6 - month_end.weekday()))
    
    # 週データを生成
    weeks = []
    current_date = calendar_start
    
    while current_date <= last_sunday_of_month:
        week = []
        for day_num in range(7):
            is_current_month = (current_date >= month_start and current_date <= month_end)
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
    
    # 年・月の取得（デフォルトは今月）
    today = date.today()
    selected_year_str = request.GET.get('year', str(today.year))
    selected_month_str = request.GET.get('month', str(today.month))
    
    try:
        selected_year = int(selected_year_str)
        selected_month = int(selected_month_str)
        
        # 月の範囲チェック
        if selected_month < 1 or selected_month > 12:
            selected_year = today.year
            selected_month = today.month
        
        # 選択された月の日付範囲を取得
        month_start = date(selected_year, selected_month, 1)
        if selected_month == 12:
            month_end = date(selected_year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(selected_year, selected_month + 1, 1) - timedelta(days=1)
            
    except (ValueError, TypeError):
        # 無効な値の場合は今月を使用
        selected_year = today.year
        selected_month = today.month
        month_start = today.replace(day=1)
        if today.month == 12:
            month_end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    
    # 選択月のシフトを取得
    # 開始日が選択月内、または終了日が選択月内のシフトを取得
    shifts = Shift.objects.filter(
        staff=staff
    ).filter(
        Q(date__gte=month_start, date__lte=month_end) |  # 開始日が選択月内
        Q(end_date__gte=month_start, end_date__lte=month_end) |  # 終了日が選択月内
        Q(date__lt=month_start, end_date__gte=month_start, end_date__lte=month_end)  # 前月から続くシフトの当月部分
    ).order_by('date', 'start_time')
    
    # シフトがある日だけのリストを作成
    monthly_shifts = []
    # シフトを日付ごとにグループ化（選択月内の日付のみ）
    shifts_by_date = {}
    for shift in shifts:
        # シフトの開始日が選択月内の場合
        if month_start <= shift.date <= month_end:
            shift_date = shift.date
            if shift_date not in shifts_by_date:
                shifts_by_date[shift_date] = []
            shifts_by_date[shift_date].append(shift)
        
        # 前月から続くシフトの終了日が選択月内の場合（開始日は選択月外だが終了日が選択月内）
        if shift.end_date and shift.date < month_start and month_start <= shift.end_date <= month_end:
            shift_date = shift.end_date
            if shift_date not in shifts_by_date:
                shifts_by_date[shift_date] = []
            shifts_by_date[shift_date].append(shift)
    
    # 日付順にソート
    sorted_dates = sorted(shifts_by_date.keys())
    
    # 各日付に対してシフト情報を取得（同じ日に複数のシフトがある場合も含む）
    for shift_date in sorted_dates:
        day_shifts = shifts_by_date[shift_date]
        # 各シフトを個別のエントリとして追加
        for shift in day_shifts:
            monthly_shifts.append({
                'date': shift_date,
                'shift': shift
            })
    
    # シフト数の集計
    shift_count = len(monthly_shifts)
    confirmed_shift_count = len([day for day in monthly_shifts if day['shift'] and day['shift'].is_confirmed])
    
    # 前月・次月の計算
    if selected_month == 1:
        prev_year = selected_year - 1
        prev_month = 12
    else:
        prev_year = selected_year
        prev_month = selected_month - 1
    
    if selected_month == 12:
        next_year = selected_year + 1
        next_month = 1
    else:
        next_year = selected_year
        next_month = selected_month + 1
    
    # 年と月の選択肢を生成
    years = list(range(2020, 2031))  # 2020年から2030年まで
    months = list(range(1, 13))  # 1月から12月まで
    
    context = {
        'staff': staff,
        'shifts': shifts,  # 既存のコードとの互換性のため
        'monthly_shifts': monthly_shifts,
        'shift_count': shift_count,
        'confirmed_shift_count': confirmed_shift_count,
        'month_start': month_start,
        'month_end': month_end,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
        'today': today,
        'years': years,
        'months': months,
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
    if staff.employment_type != 'fixed':
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


@login_required
@staff_required
def shift_swap_list(request):
    """シフト交代募集一覧"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    # 期限切れの募集を自動的に締切にする
    today = date.today()
    expired_requests = ShiftSwapRequest.objects.filter(
        shift__store=store,
        status='open',
        date__lte=today + timedelta(days=1)
    )
    expired_requests.update(status='closed')
    
    # 自分の店舗の募集を取得（募集者以外、かつ公開中）
    swap_requests = ShiftSwapRequest.objects.filter(
        shift__store=store,
        status='open'
    ).exclude(requested_by=staff).select_related('shift', 'requested_by', 'shift__staff').order_by('date', 'start_time')
    
    # 自分の立候補状況と各募集の立候補数を取得
    my_applications = {}
    for swap_req in swap_requests:
        try:
            application = ShiftSwapApplication.objects.get(
                swap_request=swap_req,
                applicant=staff
            )
            my_applications[swap_req.id] = application
        except ShiftSwapApplication.DoesNotExist:
            pass
        # 立候補数を計算
        swap_req.application_count = swap_req.applications.filter(status='pending').count()
    
    context = {
        'staff': staff,
        'store': store,
        'swap_requests': swap_requests,
        'my_applications': my_applications,
    }
    return render(request, 'staff/shift_swap_list.html', context)


@login_required
@staff_required
def shift_swap_create(request):
    """シフト交代募集作成"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    # 自分の確定済みシフトを取得
    today = date.today()
    my_shifts = Shift.objects.filter(
        staff=staff,
        store=store,
        is_confirmed=True,
        date__gte=today
    ).order_by('date', 'start_time')
    
    # 各シフトの期限を計算
    for shift in my_shifts:
        shift.deadline = shift.date - timedelta(days=1)
        shift.is_available_for_swap = shift.deadline >= today
    
    if request.method == 'POST':
        shift_id = request.POST.get('shift_id')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        
        try:
            shift = Shift.objects.get(id=shift_id, staff=staff, store=store)
            
            # 期限チェック（出勤日の1日前まで）
            deadline = shift.date - timedelta(days=1)
            if date.today() > deadline:
                messages.error(request, f"このシフトの交代募集は締め切られています。出勤日の1日前までに募集してください。")
                return redirect('staff_shift:shift_swap_list')
            
            # 既に募集が存在するかチェック
            existing_request = ShiftSwapRequest.objects.filter(
                shift=shift,
                status__in=['open', 'pending']
            ).first()
            
            if existing_request:
                messages.warning(request, "このシフトの交代募集は既に作成されています。")
                return redirect('staff_shift:shift_swap_list')
            
            # シフト交代募集を作成
            swap_request = ShiftSwapRequest.objects.create(
                shift=shift,
                requested_by=staff,
                date=shift.date,
                start_time=datetime.strptime(start_time, '%H:%M').time() if start_time else shift.start_time,
                end_time=datetime.strptime(end_time, '%H:%M').time() if end_time else shift.end_time,
                status='open'
            )
            
            messages.success(request, "シフト交代募集を作成しました。")
            return redirect('staff_shift:shift_swap_list')
            
        except Shift.DoesNotExist:
            messages.error(request, "シフトが見つかりません。")
        except ValueError:
            messages.error(request, "無効な時間形式です。")
    
    context = {
        'staff': staff,
        'store': store,
        'my_shifts': my_shifts,
        'today': today,
    }
    return render(request, 'staff/shift_swap_create.html', context)


@login_required
@staff_required
def shift_swap_apply(request, swap_request_id):
    """シフト交代立候補"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    swap_request = get_object_or_404(
        ShiftSwapRequest,
        id=swap_request_id,
        shift__store=store,
        status='open'
    )
    
    # 募集者本人は立候補できない
    if swap_request.requested_by == staff:
        messages.error(request, "自分の募集には立候補できません。")
        return redirect('staff_shift:shift_swap_list')
    
    # 期限チェック
    if not swap_request.is_available:
        messages.error(request, "この募集は締め切られています。")
        return redirect('staff_shift:shift_swap_list')
    
    # 既に立候補しているかチェック
    existing_application = ShiftSwapApplication.objects.filter(
        swap_request=swap_request,
        applicant=staff
    ).first()
    
    if request.method == 'POST':
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        message = request.POST.get('message', '')
        
        try:
            start_time_obj = datetime.strptime(start_time, '%H:%M').time()
            end_time_obj = datetime.strptime(end_time, '%H:%M').time()
            
            if existing_application:
                # 既存の立候補を更新
                existing_application.start_time = start_time_obj
                existing_application.end_time = end_time_obj
                existing_application.message = message
                existing_application.status = 'pending'
                existing_application.save()
                messages.success(request, "立候補内容を更新しました。")
            else:
                # 新しい立候補を作成
                ShiftSwapApplication.objects.create(
                    swap_request=swap_request,
                    applicant=staff,
                    start_time=start_time_obj,
                    end_time=end_time_obj,
                    message=message,
                    status='pending'
                )
                messages.success(request, "立候補しました。")
            
            return redirect('staff_shift:shift_swap_list')
            
        except ValueError:
            messages.error(request, "無効な時間形式です。")
    
    context = {
        'staff': staff,
        'store': store,
        'swap_request': swap_request,
        'existing_application': existing_application,
    }
    return render(request, 'staff/shift_swap_apply.html', context)


@login_required
@staff_required
def shift_swap_my_requests(request):
    """自分のシフト交代募集一覧"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    # 期限切れの募集を自動的に締切にする
    today = date.today()
    expired_requests = ShiftSwapRequest.objects.filter(
        requested_by=staff,
        status='open',
        date__lte=today + timedelta(days=1)
    )
    expired_requests.update(status='closed')
    
    # 自分の募集を取得
    my_swap_requests = ShiftSwapRequest.objects.filter(
        requested_by=staff
    ).select_related('shift').prefetch_related('applications__applicant').order_by('-created_at')
    
    # 各募集の立候補者を取得
    for swap_req in my_swap_requests:
        swap_req.applications_list = [app for app in swap_req.applications.all() if app.status == 'pending']
    
    context = {
        'staff': staff,
        'store': store,
        'my_swap_requests': my_swap_requests,
    }
    return render(request, 'staff/shift_swap_my_requests.html', context)


@login_required
@staff_required
def shift_swap_cancel(request, swap_request_id):
    """シフト交代募集キャンセル"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    swap_request = get_object_or_404(
        ShiftSwapRequest,
        id=swap_request_id,
        requested_by=staff
    )
    
    if request.method == 'POST':
        swap_request.status = 'cancelled'
        swap_request.save()
        messages.success(request, "シフト交代募集をキャンセルしました。")
        return redirect('staff_shift:shift_swap_my_requests')
    
    context = {
        'swap_request': swap_request,
    }
    return render(request, 'staff/shift_swap_cancel.html', context)
