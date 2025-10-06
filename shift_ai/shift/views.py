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


@login_required
def shift_creation(request):
    """シフト作成画面"""
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
    
    context = {
        'store': store,
        'start_date': start_date_obj,
        'end_date': end_date_obj,
        'existing_shifts': existing_shifts,
        'shift_requests': shift_requests,
    }
    
    return render(request, 'shift/shift_creation.html', context)


@login_required
def generate_ai_shifts(request):
    """AIシフト生成"""
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
def shift_detail(request, shift_id):
    """シフト詳細・編集"""
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
        
        return redirect('shift_creation')
    
    return render(request, 'shift/shift_detail.html', {'shift': shift})


@login_required
def delete_shift(request, shift_id):
    """シフト削除"""
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
    
    return redirect('shift_creation')


@login_required
def confirm_shifts(request):
    """シフト確定"""
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
            return redirect('staff_shift_requests')
    
    context = {
        'staff': staff,
        'shift_requests': shift_requests,
        'month_start': month_start,
        'month_end': month_end,
    }
    
    return render(request, 'shift/staff_shift_requests.html', context)


@login_required
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
    
    context = {
        'staff': staff,
        'shifts': shifts,
        'total_hours': total_hours,
        'hall_skill_percentage': hall_skill_percentage,
        'kitchen_skill_percentage': kitchen_skill_percentage,
        'month_start': month_start,
        'month_end': month_end,
    }
    
    return render(request, 'shift/staff_shift_view.html', context)
