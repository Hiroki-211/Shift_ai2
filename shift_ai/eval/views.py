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


@login_required
def evaluation_input(request):
    """評価入力画面"""
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
            return redirect('evaluation_input')
    else:
        form = EvaluationForm()
    
    context = {
        'target_staff': target_staff,
        'evaluations': evaluations,
        'form': form,
        'period': period,
    }
    
    return render(request, 'eval/evaluation_input.html', context)


@login_required
def evaluation_detail(request, evaluation_id):
    """評価詳細・編集"""
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
            return redirect('evaluation_input')
    else:
        form = EvaluationForm(instance=evaluation)
    
    return render(request, 'eval/evaluation_detail.html', {'form': form, 'evaluation': evaluation})


@login_required
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
    
    return render(request, 'eval/staff_evaluation_view.html', context)


@login_required
def attendance_records(request):
    """勤怠記録管理"""
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
            return redirect('attendance_records')
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
    
    return render(request, 'eval/attendance_records.html', context)


@login_required
def attendance_detail(request, record_id):
    """勤怠記録詳細・編集"""
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
            return redirect('attendance_records')
    else:
        form = AttendanceRecordForm(instance=record)
    
    return render(request, 'eval/attendance_detail.html', {'form': form, 'record': record})


@login_required
def evaluation_reports(request):
    """評価レポート"""
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
    
    context = {
        'store': store,
        'period_stats': period_stats,
    }
    
    return render(request, 'eval/evaluation_reports.html', context)
