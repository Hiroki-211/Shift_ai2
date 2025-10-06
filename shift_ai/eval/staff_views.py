from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Avg
from datetime import datetime, date, timedelta
from .models import Evaluation, AttendanceRecord
from .forms import AttendanceRecordForm
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
def staff_evaluation_view(request):
    """スタッフ評価結果確認"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    # 自分の評価結果を取得
    evaluations = Evaluation.objects.filter(
        staff=staff
    ).order_by('-evaluation_period')
    
    # 最新の評価
    latest_evaluation = evaluations.first()
    
    # 評価推移データ
    evaluation_history = []
    for eval in evaluations:
        evaluation_history.append({
            'period': eval.evaluation_period,
            'total_score': eval.total_score,
            'attendance_score': eval.attendance_score,
            'skill_score': eval.skill_score,
            'teamwork_score': eval.teamwork_score,
            'customer_service_score': eval.customer_service_score,
        })
    
    # 平均スコア計算
    avg_scores = evaluations.aggregate(
        avg_total=Avg('total_score'),
        avg_attendance=Avg('attendance_score'),
        avg_skill=Avg('skill_score'),
        avg_teamwork=Avg('teamwork_score'),
        avg_customer_service=Avg('customer_service_score')
    )
    
    context = {
        'staff': staff,
        'evaluations': evaluations,
        'latest_evaluation': latest_evaluation,
        'evaluation_history': evaluation_history,
        'avg_scores': avg_scores,
    }
    
    return render(request, 'staff/evaluation_view.html', context)


@login_required
@staff_required
def staff_attendance_records(request):
    """スタッフ勤怠記録管理"""
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
        staff=staff,
        date__range=[month_start, month_end]
    ).order_by('-date')
    
    # 勤務時間集計
    total_work_hours = sum(record.work_hours for record in attendance_records)
    avg_work_hours = total_work_hours / len(attendance_records) if attendance_records else 0
    
    if request.method == 'POST':
        # 勤怠記録の追加
        form = AttendanceRecordForm(request.POST)
        if form.is_valid():
            attendance_record = form.save(commit=False)
            attendance_record.staff = staff
            attendance_record.save()
            messages.success(request, "勤怠記録を追加しました。")
            return redirect('staff_eval:attendance_records')
    else:
        form = AttendanceRecordForm()
    
    context = {
        'staff': staff,
        'attendance_records': attendance_records,
        'form': form,
        'total_work_hours': total_work_hours,
        'avg_work_hours': avg_work_hours,
        'month_start': month_start,
        'month_end': month_end,
    }
    
    return render(request, 'staff/attendance_records.html', context)


@login_required
@staff_required
def staff_attendance_detail(request, record_id):
    """スタッフ用勤怠記録詳細・編集"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    record = get_object_or_404(AttendanceRecord, id=record_id, staff=staff)
    
    if request.method == 'POST':
        form = AttendanceRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, "勤怠記録を更新しました。")
            return redirect('staff_eval:attendance_records')
    else:
        form = AttendanceRecordForm(instance=record)
    
    return render(request, 'staff/attendance_detail.html', {'form': form, 'record': record})


@login_required
@staff_required
def staff_attendance_delete(request, record_id):
    """スタッフ用勤怠記録削除"""
    try:
        staff = request.user.staff
        store = staff.store
    except Staff.DoesNotExist:
        messages.error(request, "スタッフ情報が見つかりません。")
        return redirect('login')
    
    record = get_object_or_404(AttendanceRecord, id=record_id, staff=staff)
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, "勤怠記録を削除しました。")
        return redirect('staff_eval:attendance_records')
    
    return render(request, 'staff/attendance_delete.html', {'record': record})
