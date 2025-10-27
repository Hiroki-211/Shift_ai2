from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from datetime import datetime, date, timedelta
from .models import Shift, ShiftRequest
from .ai_shift_generator import AIShiftGenerator
from accounts.models import Store, Staff


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
    
    # 日付範囲の設定
    today = date.today()
    start_date = request.GET.get('start_date', today.strftime('%Y-%m-%d'))
    end_date = request.GET.get('end_date', (today + timedelta(days=30)).strftime('%Y-%m-%d'))
    
    try:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        start_date_obj = today
        end_date_obj = today + timedelta(days=30)
    
    # 既存のシフトを取得
    existing_shifts = Shift.objects.filter(
        store=store,
        date__range=[start_date_obj, end_date_obj]
    ).order_by('date', 'start_time')
    
    # 希望シフトを取得
    shift_requests = ShiftRequest.objects.filter(
        staff__store=store,
        date__range=[start_date_obj, end_date_obj]
    ).order_by('date')
    
    # シフト統計を計算
    total_shifts = existing_shifts.count()
    confirmed_shifts = existing_shifts.filter(is_confirmed=True).count()
    unconfirmed_shifts = total_shifts - confirmed_shifts
    total_cost = sum(shift.wage_cost for shift in existing_shifts.filter(is_confirmed=True))
    
    context = {
        'store': store,
        'start_date': start_date_obj,
        'end_date': end_date_obj,
        'existing_shifts': existing_shifts,
        'shift_requests': shift_requests,
        'total_shifts': total_shifts,
        'confirmed_shifts': confirmed_shifts,
        'unconfirmed_shifts': unconfirmed_shifts,
        'total_cost': total_cost,
    }
    
    return render(request, 'admin/shift_creation.html', context)


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
    
    shift_requests = ShiftRequest.objects.filter(
        staff__store=store,
        date__range=[month_start, month_end]
    ).order_by('date', 'staff__user__last_name')
    
    context = {
        'store': store,
        'shift_requests': shift_requests,
        'month_start': month_start,
        'month_end': month_end,
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
    
    # 今月の日付範囲を取得
    today = date.today()
    month_start = today.replace(day=1)
    if today.month == 12:
        month_end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        month_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    
    # シフトを取得
    shifts = Shift.objects.filter(
        store=store,
        date__range=[month_start, month_end]
    ).order_by('date', 'start_time')
    
    context = {
        'store': store,
        'month_start': month_start,
        'month_end': month_end,
        'shifts': shifts,
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
    else:
        next_month_start = date(today.year, today.month + 1, 1)
    
    if next_month_start.month == 12:
        next_month_end = date(next_month_start.year + 1, 1, 1) - timedelta(days=1)
    else:
        next_month_end = date(next_month_start.year, next_month_start.month + 1, 1) - timedelta(days=1)
    
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
            'name': staff_member.user.get_full_name() or staff_member.user.username,
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
    
    context = {
        'store': store,
        'month_start': next_month_start,
        'month_end': next_month_end,
        'staff_status_list': staff_status_list,
        'submitted_count': submitted_count,
        'not_submitted_count': total_count - submitted_count,
        'submission_rate': submission_rate,
        'total_requests': total_requests,
    }
    
    return render(request, 'admin/shift_submission_status.html', context)
