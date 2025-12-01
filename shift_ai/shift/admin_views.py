from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from datetime import datetime, date, timedelta
import calendar
import json
from .models import Shift, ShiftRequest, ShiftSettings, ChatRoom, ChatMessage, ShiftSwapRequest
from .forms import ShiftSettingsForm, ChatMessageForm
from .ai_shift_generator import AIShiftGenerator
from accounts.models import Store, Staff


def get_staff_name_japanese(user):
    """日本語形式の名前を取得（姓 名の順）"""
    if user.last_name and user.first_name:
        return f"{user.last_name} {user.first_name}".strip()
    elif user.last_name:
        return user.last_name
    elif user.first_name:
        return user.first_name
    else:
        return user.username


def admin_required(view_func):
    """管理者権限が必要なデコレータ"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        try:
            staff = request.user.staff
            if not staff.is_manager:
                messages.error(request, "管理者権限が必要です。")
                return redirect('staff_accounts:dashboard')
        except Staff.DoesNotExist:
            messages.error(request, "スタッフ情報が見つかりません。")
            return redirect('login')
        
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@admin_required
def admin_shift_creation(request):
    """管理者用シフト作成画面"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    # 月の前半・後半・すべての選択設定（デフォルトは今月すべて）
    today = date.today()
    
    # 年・月・期間の取得
    selected_year_str = request.GET.get('year', str(today.year))
    selected_month_str = request.GET.get('month', str(today.month))
    period = request.GET.get('period', 'all')  # 'first_half', 'second_half', 'all'
    
    try:
        selected_year_int = int(selected_year_str)
        selected_month_int = int(selected_month_str)
        
        # 月の日数を取得
        _, last_day = calendar.monthrange(selected_year_int, selected_month_int)
        
        # 期間に応じて開始日と終了日を設定
        if period == 'first_half':
            # 前半：1日～15日
            start_date_obj = date(selected_year_int, selected_month_int, 1)
            end_date_obj = date(selected_year_int, selected_month_int, min(15, last_day))
        elif period == 'second_half':
            # 後半：16日～月末
            start_date_obj = date(selected_year_int, selected_month_int, 16)
            end_date_obj = date(selected_year_int, selected_month_int, last_day)
        else:
            # すべて：1日～月末
            start_date_obj = date(selected_year_int, selected_month_int, 1)
            end_date_obj = date(selected_year_int, selected_month_int, last_day)
            
    except (ValueError, calendar.IllegalMonthError):
        # エラー時は今月すべてを使用
        _, last_day = calendar.monthrange(today.year, today.month)
        start_date_obj = date(today.year, today.month, 1)
        end_date_obj = date(today.year, today.month, last_day)
        selected_year_int = today.year
        selected_month_int = today.month
        period = 'all'
    
    # 既存のシフトを取得
    existing_shifts = Shift.objects.filter(
        store=store,
        date__range=[start_date_obj, end_date_obj]
    ).select_related('staff', 'staff__user').order_by('date', 'start_time')
    
    # 日付ごとにシフトをグループ化
    shifts_by_date = {}
    for shift in existing_shifts:
        shift_date = shift.date
        if shift_date not in shifts_by_date:
            shifts_by_date[shift_date] = []
        shifts_by_date[shift_date].append(shift)
    
    # 日付ごとのスタッフ数を計算
    date_summary = []
    for shift_date in sorted(shifts_by_date.keys()):
        shifts_on_date = shifts_by_date[shift_date]
        staff_count = len(set(shift.staff.id for shift in shifts_on_date))
        confirmed_count = sum(1 for shift in shifts_on_date if shift.is_confirmed)
        total_cost_on_date = sum(shift.wage_cost for shift in shifts_on_date if shift.is_confirmed)
        
        date_summary.append({
            'date': shift_date,
            'staff_count': staff_count,
            'total_shifts': len(shifts_on_date),
            'confirmed_shifts': confirmed_count,
            'unconfirmed_shifts': len(shifts_on_date) - confirmed_count,
            'total_cost': total_cost_on_date,
            'shifts': shifts_on_date,
        })
    
    # シフト統計を計算
    total_shifts = existing_shifts.count()
    confirmed_shifts = existing_shifts.filter(is_confirmed=True).count()
    unconfirmed_shifts = total_shifts - confirmed_shifts
    total_cost = sum(shift.wage_cost for shift in existing_shifts.filter(is_confirmed=True))
    
    # 年と月の選択肢を準備
    current_year = today.year
    years = list(range(current_year - 1, current_year + 3))  # 過去1年から未来2年まで
    months = list(range(1, 13))
    
    # 期間の選択肢
    period_choices = [
        ('first_half', '前半'),
        ('second_half', '後半'),
        ('all', 'すべて'),
    ]
    
    context = {
        'store': store,
        'start_date': start_date_obj,
        'end_date': end_date_obj,
        'selected_year': selected_year_int,
        'selected_month': selected_month_int,
        'period': period,
        'years': years,
        'months': months,
        'period_choices': period_choices,
        'existing_shifts': existing_shifts,
        'date_summary': date_summary,
        'total_shifts': total_shifts,
        'confirmed_shifts': confirmed_shifts,
        'unconfirmed_shifts': unconfirmed_shifts,
        'total_cost': total_cost,
    }
    
    return render(request, 'admin/shift_creation.html', context)


@login_required
@admin_required
def admin_shift_detail_by_date(request, shift_date):
    """指定日のシフト詳細をJSONで返す（ガントチャート用）"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        return JsonResponse({'error': 'スタッフ情報が見つかりません。'}, status=400)
    
    try:
        target_date = datetime.strptime(shift_date, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': '無効な日付形式です。'}, status=400)
    
    # その日のシフトを取得
    previous_date = target_date - timedelta(days=1)
    next_date = target_date + timedelta(days=1)
    
    # 1. 当日開始のシフト（当日に開始して当日または翌日に終了）
    shifts_today = Shift.objects.filter(
        store=store,
        date=target_date
    ).select_related('staff', 'staff__user')
    
    # 2. 前日から続くシフトの当日部分（前日に開始して当日に終了するシフトの0時〜終了時刻）
    shifts_from_previous = Shift.objects.filter(
        store=store,
        date=previous_date,
        end_date=target_date
    ).select_related('staff', 'staff__user')
    
    # 3. 当日開始で翌日に終了するシフトの前日部分（当日に開始して翌日に終了するシフトの開始時刻〜23時）
    # これは前日のガントチャートで表示されるため、ここでは取得しない
    
    # シフトを結合
    shifts = list(shifts_today) + list(shifts_from_previous)
    shifts.sort(key=lambda s: (s.staff.user.last_name or s.staff.user.username, s.start_time))
    
    # ガントチャート用のデータを準備
    gantt_data = []
    for shift in shifts:
        start_hour, start_min = shift.start_time.hour, shift.start_time.minute
        end_hour, end_min = shift.end_time.hour, shift.end_time.minute
        
        # シフトの開始日と終了日を取得
        shift_start_date = shift.date
        shift_end_date = shift.end_date if shift.end_date else shift.date
        
        # 日をまたぐかどうか
        spans_midnight = shift_end_date > shift_start_date or (shift_end_date == shift_start_date and end_hour < start_hour)
        
        # 前日から続くシフトの場合、当日の部分（0時〜終了時刻）のみを表示
        if spans_midnight and shift_start_date == previous_date:
            # 前日から続くシフトの当日部分：0時〜終了時刻
            gantt_data.append({
                'staff_id': shift.staff.id,
                'staff_name': get_staff_name_japanese(shift.staff.user),
                'start_time': shift.start_time.strftime('%H:%M'),
                'end_time': shift.end_time.strftime('%H:%M'),
                'start_minutes': 0,  # 当日の0時から
                'end_minutes': end_hour * 60 + end_min,  # 当日の終了時刻まで
                'spans_midnight': False,  # 当日のガントチャートでは日をまたがない
                'is_from_previous': True,  # 前日から続くシフトの当日部分
                'duration_hours': shift.duration_hours,
                'is_confirmed': shift.is_confirmed,
                'shift_id': shift.id,
            })
        elif shift_start_date == target_date:
            # 当日開始のシフト
            start_minutes = start_hour * 60 + start_min
            
            # 日をまたぐ場合（当日中に開始して翌日に終了）
            # 当日のガントチャートには開始時刻〜23時59分までしか表示しない
            if spans_midnight:
                # 当日の部分のみを表示（開始時刻〜23時59分）
                end_minutes = 24 * 60  # 23時59分まで
            else:
                # 当日中に終了するシフト
                end_minutes = end_hour * 60 + end_min
            
            gantt_data.append({
                'staff_id': shift.staff.id,
                'staff_name': get_staff_name_japanese(shift.staff.user),
                'start_time': shift.start_time.strftime('%H:%M'),
                'end_time': shift.end_time.strftime('%H:%M'),
                'start_minutes': start_minutes,
                'end_minutes': end_minutes,
                'spans_midnight': False,  # 当日のガントチャートでは日をまたがない
                'is_from_previous': False,
                'duration_hours': shift.duration_hours,
                'is_confirmed': shift.is_confirmed,
                'shift_id': shift.id,
            })
    
    return JsonResponse({
        'date': target_date.strftime('%Y-%m-%d'),
        'date_display': target_date.strftime('%Y年%m月%d日'),
        'shifts': gantt_data,
    })


@login_required
@admin_required
def admin_generate_ai_shifts(request):
    """管理者用AIシフト生成"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        return JsonResponse({'error': 'スタッフ情報が見つかりません。'}, status=400)
    
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': '無効な日付形式です。'}, status=400)
        
        # AIシフト生成
        generator = AIShiftGenerator(store)
        generated_shifts = generator.generate_shifts(start_date_obj, end_date_obj)
        
        # 制約チェック
        errors = generator.validate_shift_constraints(generated_shifts)
        if errors:
            return JsonResponse({'error': 'シフト制約エラー', 'details': errors}, status=400)
        
        # シフトを保存
        created_shifts = []
        for shift_data in generated_shifts:
            shift, created = Shift.objects.get_or_create(
                store=shift_data['store'],
                staff=shift_data['staff'],
                date=shift_data['date'],
                start_time=shift_data['start_time'],
                defaults={
                    'end_time': shift_data['end_time'],
                    'is_confirmed': shift_data['is_confirmed']
                }
            )
            if created:
                created_shifts.append(shift)
        
        # 人件費計算
        total_cost = generator.calculate_shift_cost(generated_shifts)
        
        return JsonResponse({
            'success': True,
            'created_count': len(created_shifts),
            'total_cost': total_cost,
            'message': f'{len(created_shifts)}件のシフトを生成しました。'
        })
    
    return JsonResponse({'error': '無効なリクエストです。'}, status=400)


@login_required
@admin_required
def admin_shift_detail(request, shift_id):
    """管理者用シフト詳細・編集"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    shift = get_object_or_404(Shift, id=shift_id, store=store)
    
    if request.method == 'POST':
        # シフト編集
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        is_confirmed = request.POST.get('is_confirmed') == 'on'
        
        try:
            shift.start_time = datetime.strptime(start_time, '%H:%M').time()
            shift.end_time = datetime.strptime(end_time, '%H:%M').time()
            shift.is_confirmed = is_confirmed
            shift.save()
            messages.success(request, "シフトを更新しました。")
        except ValueError:
            messages.error(request, "無効な時間形式です。")
        
        return redirect('admin_shift:shift_creation')
    
    return render(request, 'admin/shift_detail.html', {'shift': shift})


@login_required
@admin_required
def admin_delete_shift(request, shift_id):
    """管理者用シフト削除"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    shift = get_object_or_404(Shift, id=shift_id, store=store)
    
    if request.method == 'POST':
        shift.delete()
        messages.success(request, "シフトを削除しました。")
    
    return redirect('admin_shift:shift_creation')


@login_required
@admin_required
def admin_create_shifts_from_requests(request):
    """希望シフトからシフトを作成"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        return JsonResponse({'error': 'スタッフ情報が見つかりません。'}, status=400)
    
    if request.method == 'POST':
        request_ids = request.POST.getlist('request_ids')
        
        if not request_ids:
            return JsonResponse({'error': 'シフトを作成する希望を選択してください。'}, status=400)
        
        created_shifts = []
        skipped_shifts = []
        errors = []
        
        for request_id in request_ids:
            try:
                shift_request = ShiftRequest.objects.get(id=request_id, staff__store=store)
                
                # 勤務希望のみシフトを作成
                if shift_request.request_type != 'work':
                    skipped_shifts.append({
                        'id': shift_request.id,
                        'reason': '勤務希望ではありません'
                    })
                    continue
                
                # 開始時刻と終了時刻が設定されているかチェック
                if not shift_request.start_time or not shift_request.end_time:
                    skipped_shifts.append({
                        'id': shift_request.id,
                        'reason': '希望時間が設定されていません'
                    })
                    continue
                
                # 既に同じシフトが存在するかチェック
                existing_shift = Shift.objects.filter(
                    store=store,
                    staff=shift_request.staff,
                    date=shift_request.date,
                    start_time=shift_request.start_time
                ).first()
                
                if existing_shift:
                    skipped_shifts.append({
                        'id': shift_request.id,
                        'reason': '既にシフトが存在します'
                    })
                    continue
                
                # シフトを作成
                shift = Shift.objects.create(
                    store=store,
                    staff=shift_request.staff,
                    date=shift_request.date,
                    start_time=shift_request.start_time,
                    end_time=shift_request.end_time,
                    end_date=shift_request.end_date,
                    is_confirmed=False
                )
                created_shifts.append(shift)
                
            except ShiftRequest.DoesNotExist:
                errors.append(f'ID {request_id}: 希望シフトが見つかりません')
            except Exception as e:
                errors.append(f'ID {request_id}: {str(e)}')
        
        message_parts = []
        if created_shifts:
            message_parts.append(f'{len(created_shifts)}件のシフトを作成しました')
        if skipped_shifts:
            message_parts.append(f'{len(skipped_shifts)}件をスキップしました')
        if errors:
            message_parts.append(f'{len(errors)}件のエラーが発生しました')
        
        return JsonResponse({
            'success': True,
            'created_count': len(created_shifts),
            'skipped_count': len(skipped_shifts),
            'error_count': len(errors),
            'message': '。'.join(message_parts) + '。',
            'skipped_details': skipped_shifts[:5]  # 最初の5件のみ
        })
    
    return JsonResponse({'error': '無効なリクエストです。'}, status=400)


@login_required
@admin_required
def admin_confirm_shifts(request):
    """管理者用シフト確定"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        return JsonResponse({'error': 'スタッフ情報が見つかりません。'}, status=400)
    
    if request.method == 'POST':
        shift_ids = request.POST.getlist('shift_ids')
        
        if not shift_ids:
            return JsonResponse({'error': 'シフトが選択されていません。'}, status=400)
        
        # シフトを確定
        updated_count = Shift.objects.filter(
            id__in=shift_ids,
            store=store
        ).update(is_confirmed=True)
        
        return JsonResponse({
            'success': True,
            'updated_count': updated_count,
            'message': f'{updated_count}件のシフトを確定しました。'
        })
    
    return JsonResponse({'error': '無効なリクエストです。'}, status=400)


@login_required
@admin_required
def admin_staff_shift_requests(request):
    """管理者用スタッフ希望シフト確認"""
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
    
    # 過去3ヶ月から未来3ヶ月までの希望シフトを取得
    start_date = (today - timedelta(days=90)).replace(day=1)
    end_date = (today + timedelta(days=90))
    if end_date.month == 12:
        end_date = end_date.replace(year=end_date.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end_date = end_date.replace(month=end_date.month + 1, day=1) - timedelta(days=1)
    
    shift_requests = ShiftRequest.objects.filter(
        staff__store=store,
        date__range=[start_date, end_date]
    ).select_related('staff', 'staff__user').order_by('date', 'staff__user__last_name')
    
    # 月ごとにグループ化
    monthly_data = {}
    for req in shift_requests:
        month_key = req.date.strftime('%Y-%m')
        month_label = req.date.strftime('%Y年%m月')
        
        if month_key not in monthly_data:
            monthly_data[month_key] = {
                'month_label': month_label,
                'month_key': month_key,
                'staffs': {},
                'total_count': 0,
            }
        
        staff_id = req.staff.id
        if staff_id not in monthly_data[month_key]['staffs']:
            monthly_data[month_key]['staffs'][staff_id] = {
                'staff': req.staff,
                'requests': [],
                'off_count': 0,
                'work_count': 0,
            }
        
        monthly_data[month_key]['staffs'][staff_id]['requests'].append(req)
        monthly_data[month_key]['total_count'] += 1
        
        if req.request_type == 'off':
            monthly_data[month_key]['staffs'][staff_id]['off_count'] += 1
        elif req.request_type == 'work':
            monthly_data[month_key]['staffs'][staff_id]['work_count'] += 1
    
    # 月ごとのデータをリストに変換（月の降順でソート）
    monthly_list = []
    for month_key in sorted(monthly_data.keys(), reverse=True):
        month_info = monthly_data[month_key]
        # 各月の従業員リストをソート
        staff_list = sorted(month_info['staffs'].values(),
                          key=lambda x: get_staff_name_japanese(x['staff'].user))
        month_info['staff_list'] = staff_list
        monthly_list.append(month_info)
    
    # 全体の集計情報を計算
    off_count = sum(sum(s['off_count'] for s in m['staff_list']) for m in monthly_list)
    work_count = sum(sum(s['work_count'] for s in m['staff_list']) for m in monthly_list)
    
    context = {
        'store': store,
        'shift_requests': shift_requests,
        'monthly_list': monthly_list,
        'month_start': month_start,
        'month_end': month_end,
        'off_count': off_count,
        'work_count': work_count,
    }
    
    return render(request, 'admin/staff_shift_requests.html', context)


@login_required
@admin_required
def admin_shift_calendar(request):
    """管理者用シフトカレンダー"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    # 表示する月を取得（GETパラメータから、または今月）
    today = date.today()
    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)
    except (ValueError, TypeError):
        month_start = today.replace(day=1)
        if today.month == 12:
            month_end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    
    # シフトを取得（当月開始のシフト + 前月から続くシフトの当月部分）
    shifts = Shift.objects.filter(
        store=store,
        date__range=[month_start, month_end]
    ).select_related('staff', 'staff__user').order_by('date', 'start_time')
    
    # 前月から続くシフトの当月部分も取得
    previous_month_end = month_start - timedelta(days=1)
    shifts_from_previous = Shift.objects.filter(
        store=store,
        date__lte=previous_month_end,
        end_date__gte=month_start
    ).select_related('staff', 'staff__user')
    
    # 日付ごとにシフトをグループ化し、各日の従業員数と人件費を計算
    shifts_by_date = {}
    
    # 当月開始のシフト
    for shift in shifts:
        shift_date = shift.date
        shift_end_date = shift.end_date if shift.end_date else shift.date
        start_hour = shift.start_time.hour
        end_hour = shift.end_time.hour
        start_min = shift.start_time.minute
        end_min = shift.end_time.minute
        
        # 日をまたぐかどうか
        spans_midnight = shift_end_date > shift_date or (shift_end_date == shift_date and end_hour < start_hour)
        
        if shift_date not in shifts_by_date:
            shifts_by_date[shift_date] = {
                'shifts': [],
                'staff_ids': set(),
                'total_cost': 0,
            }
        shifts_by_date[shift_date]['shifts'].append(shift)
        shifts_by_date[shift_date]['staff_ids'].add(shift.staff.id)
        
        if shift.is_confirmed:
            if spans_midnight:
                # 日をまたぐ場合：当日の部分（開始時刻〜23時59分）の人件費を計算
                start_datetime = datetime.combine(shift_date, shift.start_time)
                end_datetime = datetime.combine(shift_date, datetime.max.time().replace(microsecond=0))  # 23:59:59
                duration_hours = (end_datetime - start_datetime).total_seconds() / 3600
                if duration_hours < 0:
                    duration_hours += 24
                daily_cost = duration_hours * shift.staff.hourly_wage
                shifts_by_date[shift_date]['total_cost'] += daily_cost
            else:
                # 当日中に終了するシフト
                shifts_by_date[shift_date]['total_cost'] += shift.wage_cost
        
        # 日をまたぐ場合、翌日の部分も追加
        if spans_midnight and shift_end_date <= month_end:
            if shift_end_date not in shifts_by_date:
                shifts_by_date[shift_end_date] = {
                    'shifts': [],
                    'staff_ids': set(),
                    'total_cost': 0,
                }
            # 翌日の部分としてシフトを追加（表示用）
            shifts_by_date[shift_end_date]['shifts'].append(shift)
            shifts_by_date[shift_end_date]['staff_ids'].add(shift.staff.id)
            if shift.is_confirmed:
                # 翌日の部分（0時〜終了時刻）の人件費を計算
                start_datetime = datetime.combine(shift_end_date, datetime.min.time())  # 0時
                end_datetime = datetime.combine(shift_end_date, shift.end_time)
                duration_hours = (end_datetime - start_datetime).total_seconds() / 3600
                if duration_hours < 0:
                    duration_hours += 24
                daily_cost = duration_hours * shift.staff.hourly_wage
                shifts_by_date[shift_end_date]['total_cost'] += daily_cost
    
    # 前月から続くシフトの当月部分
    for shift in shifts_from_previous:
        shift_start_date = shift.date
        shift_end_date = shift.end_date if shift.end_date else shift.date
        
        # 前日部分が当月内の場合
        if month_start <= shift_start_date <= month_end:
            if shift_start_date not in shifts_by_date:
                shifts_by_date[shift_start_date] = {
                    'shifts': [],
                    'staff_ids': set(),
                    'total_cost': 0,
                }
            shifts_by_date[shift_start_date]['shifts'].append(shift)
            shifts_by_date[shift_start_date]['staff_ids'].add(shift.staff.id)
            if shift.is_confirmed:
                # 前日の部分（開始時刻〜23時59分）の人件費を計算
                start_datetime = datetime.combine(shift_start_date, shift.start_time)
                end_datetime = datetime.combine(shift_start_date, datetime.max.time().replace(microsecond=0))  # 23:59:59
                duration_hours = (end_datetime - start_datetime).total_seconds() / 3600
                if duration_hours < 0:
                    duration_hours += 24
                daily_cost = duration_hours * shift.staff.hourly_wage
                shifts_by_date[shift_start_date]['total_cost'] += daily_cost
        
        # 当日部分が当月内の場合
        if shift_end_date and month_start <= shift_end_date <= month_end:
            if shift_end_date not in shifts_by_date:
                shifts_by_date[shift_end_date] = {
                    'shifts': [],
                    'staff_ids': set(),
                    'total_cost': 0,
                }
            # 前月から続くシフトの当日部分として追加
            shifts_by_date[shift_end_date]['shifts'].append(shift)
            shifts_by_date[shift_end_date]['staff_ids'].add(shift.staff.id)
            if shift.is_confirmed:
                # 当日部分（0時〜終了時刻）の人件費を計算
                end_datetime = datetime.combine(shift_end_date, shift.end_time)
                start_datetime = datetime.combine(shift_end_date, datetime.min.time())  # 当日の0時
                duration_hours = (end_datetime - start_datetime).total_seconds() / 3600
                if duration_hours < 0:
                    duration_hours += 24
                daily_cost = duration_hours * shift.staff.hourly_wage
                shifts_by_date[shift_end_date]['total_cost'] += daily_cost
    
    # 前月から続くシフトも含めてJSON形式で準備
    all_shifts_for_json = list(shifts) + list(shifts_from_previous)
    
    # シフトデータをJSON形式で準備（日をまたぐシフトは両方の日に含める）
    shifts_json = []
    for shift in all_shifts_for_json:
        shift_date = shift.date
        shift_end_date = shift.end_date if shift.end_date else shift.date
        start_hour = shift.start_time.hour
        end_hour = shift.end_time.hour
        
        # 日をまたぐかどうか
        spans_midnight = shift_end_date > shift_date or (shift_end_date == shift_date and end_hour < start_hour)
        
        # 開始日のシフトデータ
        if month_start <= shift_date <= month_end:
            shifts_json.append({
                'id': shift.id,
                'date': shift_date.strftime('%Y-%m-%d'),
                'start_time': shift.start_time.strftime('%H:%M'),
                'end_time': shift.end_time.strftime('%H:%M'),
                'staff_id': shift.staff.id,
                'staff_name': get_staff_name_japanese(shift.staff.user),
                'is_confirmed': shift.is_confirmed,
                'wage_cost': shift.wage_cost,
                'spans_midnight': spans_midnight,
            })
        
        # 日をまたぐ場合、終了日のシフトデータも追加
        if spans_midnight and month_start <= shift_end_date <= month_end:
            shifts_json.append({
                'id': shift.id,
                'date': shift_end_date.strftime('%Y-%m-%d'),
                'start_time': shift.start_time.strftime('%H:%M'),
                'end_time': shift.end_time.strftime('%H:%M'),
                'staff_id': shift.staff.id,
                'staff_name': get_staff_name_japanese(shift.staff.user),
                'is_confirmed': shift.is_confirmed,
                'wage_cost': shift.wage_cost,
                'spans_midnight': spans_midnight,
                'is_continuation': True,  # 前日から続くシフトの当日部分であることを示す
            })
    
    # 日付ごとの統計情報を準備
    date_stats = {}
    for shift_date, data in shifts_by_date.items():
        date_stats[shift_date.strftime('%Y-%m-%d')] = {
            'staff_count': len(data['staff_ids']),
            'total_cost': data['total_cost'],
        }
    
    # 統計情報を計算
    total_shifts = shifts.count()
    confirmed_shifts = shifts.filter(is_confirmed=True).count()
    pending_shifts = total_shifts - confirmed_shifts
    total_cost = sum(shift.wage_cost for shift in shifts.filter(is_confirmed=True))
    
    context = {
        'store': store,
        'month_start': month_start,
        'month_end': month_end,
        'shifts': shifts,
        'shifts_json': json.dumps(shifts_json, ensure_ascii=False),
        'date_stats_json': json.dumps(date_stats, ensure_ascii=False),
        'total_shifts': total_shifts,
        'confirmed_shifts': confirmed_shifts,
        'pending_shifts': pending_shifts,
        'total_cost': total_cost,
    }
    
    return render(request, 'admin/shift_calendar.html', context)


@login_required
@admin_required
def admin_shift_submission_status(request):
    """管理者用シフト提出状況確認"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    # 来月の日付範囲を取得
    today = date.today()
    if today.month == 12:
        next_month_start = date(today.year + 1, 1, 1)
        next_month_end = date(today.year + 1, 2, 1) - timedelta(days=1)
    else:
        next_month_start = date(today.year, today.month + 1, 1)
        if today.month == 11:
            next_month_end = date(today.year + 1, 1, 1) - timedelta(days=1)
        else:
            next_month_end = date(today.year, today.month + 2, 1) - timedelta(days=1)
    
    # スタッフリストを取得
    all_staff = Staff.objects.filter(store=store).select_related('user')
    
    # 各スタッフの提出状況を確認
    staff_status_list = []
    for staff_member in all_staff:
        requests = ShiftRequest.objects.filter(
            staff=staff_member,
            date__range=[next_month_start, next_month_end]
        )
        
        work_requests = requests.filter(request_type='work').count()
        off_requests = requests.filter(request_type='off').count()
        is_submitted = requests.exists()
        
        last_request = requests.order_by('-submitted_at').first()
        
        staff_status_list.append({
            'id': staff_member.id,
            'name': get_staff_name_japanese(staff_member.user),
            'employment_type': staff_member.get_employment_type_display(),
            'is_submitted': is_submitted,
            'work_requests': work_requests,
            'off_requests': off_requests,
            'submitted_at': last_request.submitted_at if last_request else None,
        })
    
    # 提出率計算
    submitted_count = sum(1 for s in staff_status_list if s['is_submitted'])
    total_count = len(staff_status_list)
    submission_rate = (submitted_count / total_count * 100) if total_count > 0 else 0
    
    # 総希望日数計算
    total_requests = sum(s['work_requests'] + s['off_requests'] for s in staff_status_list)
    
    # 提出期限を店舗設定から取得
    if next_month_start.month == 1:
        # 来月が1月の場合、前月（今月）は12月
        submission_deadline = date(today.year, 12, store.shift_submission_deadline_day)
    else:
        submission_deadline = date(today.year, today.month, store.shift_submission_deadline_day)
    
    context = {
        'store': store,
        'month_start': next_month_start,
        'month_end': next_month_end,
        'staff_status_list': staff_status_list,
        'submitted_count': submitted_count,
        'not_submitted_count': total_count - submitted_count,
        'submission_rate': submission_rate,
        'total_requests': total_requests,
        'submission_deadline': submission_deadline,
    }
    
    return render(request, 'admin/shift_submission_status.html', context)


@login_required
@admin_required
def admin_submission_detail_api(request, staff_id):
    """スタッフのシフト提出詳細を取得（API）"""
    try:
        staff = request.user.staff
        target_staff = Staff.objects.get(id=staff_id)
        
        # スタッフのストアが一致するか確認
        if staff.store != target_staff.store:
            return JsonResponse({'error': '権限がありません。'}, status=403)
    except Staff.DoesNotExist:
        return JsonResponse({'error': 'スタッフが見つかりません。'}, status=404)
    
    # 対象月を取得（リクエストパラメータまたは今月）
    target_month = request.GET.get('month')
    if target_month:
        year, month = map(int, target_month.split('-'))
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)
    else:
        # 今月
        today = date.today()
        if today.month == 12:
            month_start = date(today.year + 1, 1, 1)
            month_end = date(today.year + 1, 2, 1) - timedelta(days=1)
        else:
            month_start = date(today.year, today.month + 1, 1)
            if today.month == 11:
                month_end = date(today.year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(today.year, today.month + 2, 1) - timedelta(days=1)
    
    # シフトリクエストを取得
    requests = ShiftRequest.objects.filter(
        staff=target_staff,
        date__range=[month_start, month_end]
    ).order_by('date')
    
    # JSON形式で返す
    request_list = []
    for req in requests:
        request_list.append({
            'date': req.date.strftime('%Y-%m-%d'),
            'weekday': req.date.strftime('%a'),
            'request_type': req.get_request_type_display(),
            'start_time': req.start_time.strftime('%H:%M') if req.start_time else '',
            'end_time': req.end_time.strftime('%H:%M') if req.end_time else '',
        })
    
    return JsonResponse({
        'staff_name': get_staff_name_japanese(target_staff.user),
        'requests': request_list,
        'period': f"{month_start.strftime('%Y年%m月%d日')} 〜 {month_end.strftime('%Y年%m月%d日')}"
    })


@login_required
@admin_required
def admin_shift_settings(request):
    """管理者用シフト設定"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    # 既存の設定を取得または新規作成
    shift_settings, created = ShiftSettings.objects.get_or_create(store=store)
    
    if request.method == 'POST':
        form = ShiftSettingsForm(request.POST, instance=shift_settings)
        if form.is_valid():
            form.save()
            messages.success(request, "シフト設定を保存しました。")
            return redirect('admin_shift:shift_settings')
        else:
            messages.error(request, "入力内容にエラーがあります。")
    else:
        form = ShiftSettingsForm(instance=shift_settings)
    
    context = {
        'store': store,
        'form': form,
        'shift_settings': shift_settings,
    }
    
    return render(request, 'admin/shift_settings.html', context)


@login_required
@admin_required
def admin_chat_list(request):
    """管理者用チャット一覧"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    # 自分が参加しているチャットルームを取得
    chat_rooms = ChatRoom.objects.filter(
        Q(participant1=staff) | Q(participant2=staff),
        store=store
    ).select_related('participant1', 'participant2', 'swap_request').prefetch_related('messages').order_by('-updated_at')
    
    # 各ルームの最新メッセージと未読数を取得
    for room in chat_rooms:
        room.other_participant = room.get_other_participant(staff)
        room.unread_count = room.get_unread_count(staff)
        room.last_message = room.messages.last()
    
    # 同じ店舗のスタッフ一覧（新規チャット作成用）
    other_staff = Staff.objects.filter(store=store).exclude(id=staff.id).order_by('user__last_name', 'user__first_name')
    
    context = {
        'staff': staff,
        'store': store,
        'chat_rooms': chat_rooms,
        'other_staff': other_staff,
    }
    
    return render(request, 'admin/chat_list.html', context)


@login_required
@admin_required
def admin_chat_detail(request, room_id):
    """管理者用チャット詳細"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    room = get_object_or_404(
        ChatRoom,
        id=room_id,
        store=store
    )
    
    # 参加者チェック
    if room.participant1 != staff and room.participant2 != staff:
        messages.error(request, "このチャットルームにアクセスする権限がありません。")
        return redirect('admin_shift:chat_list')
    
    other_participant = room.get_other_participant(staff)
    
    # メッセージを取得
    messages_list = room.messages.all().select_related('sender').order_by('created_at')
    
    # 未読メッセージを既読にする
    unread_messages = room.messages.filter(is_read=False).exclude(sender=staff)
    unread_messages.update(is_read=True)
    
    # メッセージ送信処理
    if request.method == 'POST':
        form = ChatMessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.room = room
            message.sender = staff
            message.save()
            
            # ルームの更新日時を更新
            room.save()
            
            messages.success(request, "メッセージを送信しました。")
            return redirect('admin_shift:chat_detail', room_id=room.id)
    else:
        form = ChatMessageForm()
    
    context = {
        'staff': staff,
        'store': store,
        'room': room,
        'other_participant': other_participant,
        'messages_list': messages_list,
        'form': form,
    }
    
    return render(request, 'admin/chat_detail.html', context)


@login_required
@admin_required
def admin_chat_create(request, staff_id):
    """管理者用チャットルーム作成"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    other_staff = get_object_or_404(Staff, id=staff_id, store=store)
    if other_staff == staff:
        messages.error(request, "自分自身とのチャットは作成できません。")
        return redirect('admin_shift:chat_list')
    
    # チャットルームを取得または作成
    room, created = ChatRoom.get_or_create_room(
        staff1=staff,
        staff2=other_staff,
        swap_request=None,
        swap_application=None
    )
    
    return redirect('admin_shift:chat_detail', room_id=room.id)
