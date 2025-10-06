"""
AIシフト生成機能
最適化アルゴリズムを使用してシフトを自動生成
"""
from datetime import datetime, timedelta, time
from typing import List, Dict, Tuple, Optional
from django.db.models import Q
from accounts.models import Store, Staff, StaffRequirement
from shift.models import Shift, ShiftRequest


class AIShiftGenerator:
    """AIシフト生成クラス"""
    
    def __init__(self, store: Store):
        self.store = store
        self.staff_list = Staff.objects.filter(store=store)
        self.requirements = StaffRequirement.objects.filter(store=store)
    
    def generate_shifts(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        指定期間のシフトを生成
        
        Args:
            start_date: 開始日
            end_date: 終了日
            
        Returns:
            生成されたシフトのリスト
        """
        generated_shifts = []
        current_date = start_date.date()
        end_date_only = end_date.date()
        
        while current_date <= end_date_only:
            day_shifts = self._generate_daily_shifts(current_date)
            generated_shifts.extend(day_shifts)
            current_date += timedelta(days=1)
        
        return generated_shifts
    
    def _generate_daily_shifts(self, date: datetime.date) -> List[Dict]:
        """1日分のシフトを生成"""
        day_of_week = date.weekday()
        daily_requirements = self.requirements.filter(day_of_week=day_of_week)
        
        if not daily_requirements.exists():
            return []
        
        # 既存のシフトと希望を取得
        existing_shifts = Shift.objects.filter(
            store=self.store,
            date=date
        )
        
        shift_requests = ShiftRequest.objects.filter(
            staff__store=self.store,
            date=date
        )
        
        generated_shifts = []
        
        for requirement in daily_requirements:
            shifts = self._assign_staff_to_time_slot(
                date, requirement, existing_shifts, shift_requests
            )
            generated_shifts.extend(shifts)
        
        return generated_shifts
    
    def _assign_staff_to_time_slot(
        self, 
        date: datetime.date, 
        requirement: StaffRequirement,
        existing_shifts: List[Shift],
        shift_requests: List[ShiftRequest]
    ) -> List[Dict]:
        """特定の時間帯にスタッフを割り当て"""
        
        # 既に割り当て済みのスタッフを取得
        assigned_staff = existing_shifts.filter(
            start_time__lt=requirement.end_time,
            end_time__gt=requirement.start_time
        ).values_list('staff_id', flat=True)
        
        # 休み希望のスタッフを除外
        off_requests = shift_requests.filter(
            request_type='off',
            start_time__lte=requirement.start_time,
            end_time__gte=requirement.end_time
        ).values_list('staff_id', flat=True)
        
        # 勤務希望のスタッフを優先
        work_requests = shift_requests.filter(
            request_type='work',
            start_time__lte=requirement.start_time,
            end_time__gte=requirement.end_time
        )
        
        # 利用可能なスタッフを取得
        available_staff = self.staff_list.exclude(
            id__in=assigned_staff
        ).exclude(
            id__in=off_requests
        )
        
        # 責任者が必要な場合
        managers_needed = requirement.required_managers
        managers_available = available_staff.filter(is_manager=True)
        
        # スキル要件を満たすスタッフ
        hall_skilled = available_staff.filter(
            hall_skill_level__gte=3
        ) if requirement.required_hall_skill > 0 else available_staff
        
        kitchen_skilled = available_staff.filter(
            kitchen_skill_level__gte=3
        ) if requirement.required_kitchen_skill > 0 else available_staff
        
        # 最適なスタッフを選択
        selected_staff = self._select_optimal_staff(
            available_staff,
            work_requests,
            managers_needed,
            hall_skilled,
            kitchen_skilled,
            requirement.required_staff
        )
        
        shifts = []
        for staff in selected_staff:
            shift_data = {
                'store': self.store,
                'staff': staff,
                'date': date,
                'start_time': requirement.start_time,
                'end_time': requirement.end_time,
                'is_confirmed': False
            }
            shifts.append(shift_data)
        
        return shifts
    
    def _select_optimal_staff(
        self,
        available_staff,
        work_requests,
        managers_needed: int,
        hall_skilled,
        kitchen_skilled,
        total_needed: int
    ) -> List[Staff]:
        """最適なスタッフを選択"""
        
        selected = []
        
        # 1. 勤務希望者を優先
        for request in work_requests:
            if len(selected) >= total_needed:
                break
            if request.staff not in selected:
                selected.append(request.staff)
        
        # 2. 責任者を確保
        managers_selected = 0
        for staff in available_staff.filter(is_manager=True):
            if managers_selected >= managers_needed or len(selected) >= total_needed:
                break
            if staff not in selected:
                selected.append(staff)
                managers_selected += 1
        
        # 3. スキル要件を満たすスタッフを追加
        for staff in hall_skilled:
            if len(selected) >= total_needed:
                break
            if staff not in selected:
                selected.append(staff)
        
        for staff in kitchen_skilled:
            if len(selected) >= total_needed:
                break
            if staff not in selected:
                selected.append(staff)
        
        # 4. 残りをランダムに選択
        remaining_staff = available_staff.exclude(id__in=[s.id for s in selected])
        for staff in remaining_staff:
            if len(selected) >= total_needed:
                break
            selected.append(staff)
        
        return selected[:total_needed]
    
    def calculate_shift_cost(self, shifts: List[Dict]) -> float:
        """シフトの人件費を計算"""
        total_cost = 0
        for shift_data in shifts:
            staff = shift_data['staff']
            start_time = shift_data['start_time']
            end_time = shift_data['end_time']
            
            # 勤務時間を計算
            start_datetime = datetime.combine(shift_data['date'], start_time)
            end_datetime = datetime.combine(shift_data['date'], end_time)
            if end_datetime <= start_datetime:
                end_datetime += timedelta(days=1)
            
            hours = (end_datetime - start_datetime).total_seconds() / 3600
            cost = hours * staff.hourly_wage
            total_cost += cost
        
        return total_cost
    
    def validate_shift_constraints(self, shifts: List[Dict]) -> List[str]:
        """シフトの制約を検証"""
        errors = []
        
        # 各スタッフの週間労働時間をチェック
        staff_weekly_hours = {}
        for shift_data in shifts:
            staff = shift_data['staff']
            date = shift_data['date']
            
            # その週の開始日を計算
            week_start = date - timedelta(days=date.weekday())
            
            if (staff, week_start) not in staff_weekly_hours:
                staff_weekly_hours[(staff, week_start)] = 0
            
            # 勤務時間を計算
            start_time = shift_data['start_time']
            end_time = shift_data['end_time']
            start_datetime = datetime.combine(date, start_time)
            end_datetime = datetime.combine(date, end_time)
            if end_datetime <= start_datetime:
                end_datetime += timedelta(days=1)
            
            hours = (end_datetime - start_datetime).total_seconds() / 3600
            staff_weekly_hours[(staff, week_start)] += hours
        
        # 週間最大労働時間をチェック
        for (staff, week_start), total_hours in staff_weekly_hours.items():
            if total_hours > staff.max_weekly_hours:
                errors.append(
                    f"{staff.user.get_full_name()}の週間労働時間が上限を超過: "
                    f"{total_hours:.1f}時間 > {staff.max_weekly_hours}時間"
                )
        
        return errors
