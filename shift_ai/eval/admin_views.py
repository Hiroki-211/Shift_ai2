from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Avg
from datetime import datetime, date, timedelta
from .models import Evaluation, AttendanceRecord
from .forms import EvaluationForm, AttendanceRecordForm
from accounts.models import Staff


def admin_required(view_func):
    """管理者権限が必要なデコレータ"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        try:
            staff = request.user.staff
            if not staff.is_manager:
                messages.error(request, "管理者権限が必要です。")
                return redirect('staff:dashboard')
        except Staff.DoesNotExist:
            messages.error(request, "スタッフ情報が見つかりません。")
            return redirect('login')
        
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@admin_required
def admin_evaluation_input(request):
    """管理者用評価入力画面"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    # 評価対象スタッフを取得
    target_staff = Staff.objects.filter(store=store)
    
    # 評価期間の設定
    current_period = datetime.now().strftime('%Y-%m')
    period = request.GET.get('period', current_period)
    
    # 既存の評価を取得
    evaluations = Evaluation.objects.filter(
        evaluator=staff,
        evaluation_period=period
    ).order_by('staff__user__last_name')
    
    if request.method == 'POST':
        staff_id = request.POST.get('staff_id')
        target_staff_obj = get_object_or_404(Staff, id=staff_id, store=store)
        
        # 評価フォームの処理
        form = EvaluationForm(request.POST)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.staff = target_staff_obj
            evaluation.evaluator = staff
            evaluation.evaluation_period = period
            evaluation.save()
            messages.success(request, f"{target_staff_obj.user.get_full_name()}の評価を保存しました。")
            return redirect('admin:evaluation_input')
    else:
        form = EvaluationForm()
    
    context = {
        'target_staff': target_staff,
        'evaluations': evaluations,
        'form': form,
        'period': period,
    }
    
    return render(request, 'admin/evaluation_input.html', context)


@login_required
@admin_required
def admin_evaluation_detail(request, evaluation_id):
    """管理者用評価詳細・編集"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    evaluation = get_object_or_404(Evaluation, id=evaluation_id, evaluator=staff)
    
    if request.method == 'POST':
        form = EvaluationForm(request.POST, instance=evaluation)
        if form.is_valid():
            form.save()
            messages.success(request, "評価を更新しました。")
            return redirect('admin:evaluation_input')
    else:
        form = EvaluationForm(instance=evaluation)
    
    return render(request, 'admin/evaluation_detail.html', {'form': form, 'evaluation': evaluation})


@login_required
@admin_required
def admin_attendance_records(request):
    """管理者用勤怠記録管理"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    # 今月の勤怠記録を取得
    today = date.today()
    month_start = today.replace(day=1)
    if today.month == 12:
        month_end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        month_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    
    attendance_records = AttendanceRecord.objects.filter(
        staff__store=store,
        date__range=[month_start, month_end]
    ).order_by('-date', 'staff__user__last_name')
    
    # スタッフ別勤務時間集計
    staff_work_hours = {}
    for record in attendance_records:
        staff_name = record.staff.user.get_full_name()
        if staff_name not in staff_work_hours:
            staff_work_hours[staff_name] = 0
        staff_work_hours[staff_name] += record.work_hours
    
    context = {
        'store': store,
        'attendance_records': attendance_records,
        'staff_work_hours': staff_work_hours,
        'month_start': month_start,
        'month_end': month_end,
    }
    
    return render(request, 'admin/attendance_records.html', context)


@login_required
@admin_required
def admin_attendance_detail(request, record_id):
    """管理者用勤怠記録詳細・編集"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    record = get_object_or_404(AttendanceRecord, id=record_id, staff__store=store)
    
    if request.method == 'POST':
        form = AttendanceRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, "勤怠記録を更新しました。")
            return redirect('admin:attendance_records')
    else:
        form = AttendanceRecordForm(instance=record)
    
    return render(request, 'admin/attendance_detail.html', {'form': form, 'record': record})


@login_required
@admin_required
def admin_evaluation_reports(request):
    """管理者用評価レポート"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    # 店舗全体の評価統計
    all_evaluations = Evaluation.objects.filter(
        staff__store=store
    ).order_by('-evaluation_period')
    
    # 期間別評価統計
    period_stats = {}
    for evaluation in all_evaluations:
        period = evaluation.evaluation_period
        if period not in period_stats:
            period_stats[period] = {
                'total_evaluations': 0,
                'avg_total_score': 0,
                'avg_attendance_score': 0,
                'avg_skill_score': 0,
                'avg_teamwork_score': 0,
                'avg_customer_service_score': 0,
            }
        
        period_stats[period]['total_evaluations'] += 1
        period_stats[period]['avg_total_score'] += evaluation.total_score
        period_stats[period]['avg_attendance_score'] += evaluation.attendance_score
        period_stats[period]['avg_skill_score'] += evaluation.skill_score
        period_stats[period]['avg_teamwork_score'] += evaluation.teamwork_score
        period_stats[period]['avg_customer_service_score'] += evaluation.customer_service_score
    
    # 平均値を計算
    for period, stats in period_stats.items():
        count = stats['total_evaluations']
        if count > 0:
            stats['avg_total_score'] = round(stats['avg_total_score'] / count, 1)
            stats['avg_attendance_score'] = round(stats['avg_attendance_score'] / count, 1)
            stats['avg_skill_score'] = round(stats['avg_skill_score'] / count, 1)
            stats['avg_teamwork_score'] = round(stats['avg_teamwork_score'] / count, 1)
            stats['avg_customer_service_score'] = round(stats['avg_customer_service_score'] / count, 1)
    
    # スタッフ別評価統計
    staff_evaluations = {}
    for evaluation in all_evaluations:
        staff_name = evaluation.staff.user.get_full_name()
        if staff_name not in staff_evaluations:
            staff_evaluations[staff_name] = []
        staff_evaluations[staff_name].append(evaluation)
    
    context = {
        'store': store,
        'period_stats': period_stats,
        'staff_evaluations': staff_evaluations,
    }
    
    return render(request, 'admin/evaluation_reports.html', context)
