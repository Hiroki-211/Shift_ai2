from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Avg
from datetime import datetime, date, timedelta
from .models import Evaluation
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

