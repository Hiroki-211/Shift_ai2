from django import forms
from .models import Evaluation, AttendanceRecord


class EvaluationForm(forms.ModelForm):
    """評価フォーム"""
    
    class Meta:
        model = Evaluation
        fields = [
            'attendance_score', 'skill_score', 'teamwork_score', 
            'customer_service_score', 'comment'
        ]
        widgets = {
            'attendance_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 30,
                'placeholder': '0-30点'
            }),
            'skill_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 40,
                'placeholder': '0-40点'
            }),
            'teamwork_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 20,
                'placeholder': '0-20点'
            }),
            'customer_service_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 10,
                'placeholder': '0-10点'
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': '評価コメントを入力してください'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        attendance_score = cleaned_data.get('attendance_score', 0)
        skill_score = cleaned_data.get('skill_score', 0)
        teamwork_score = cleaned_data.get('teamwork_score', 0)
        customer_service_score = cleaned_data.get('customer_service_score', 0)
        
        # 合計スコアの検証
        total_score = attendance_score + skill_score + teamwork_score + customer_service_score
        if total_score > 100:
            raise forms.ValidationError("合計スコアが100点を超えています。")
        
        return cleaned_data


class AttendanceRecordForm(forms.ModelForm):
    """勤怠記録フォーム"""
    
    class Meta:
        model = AttendanceRecord
        fields = [
            'date', 'clock_in', 'clock_out', 'is_late', 
            'is_early_leave', 'is_absent', 'notes'
        ]
        widgets = {
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'clock_in': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'clock_out': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'is_late': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_early_leave': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_absent': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '備考を入力してください'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        clock_in = cleaned_data.get('clock_in')
        clock_out = cleaned_data.get('clock_out')
        is_absent = cleaned_data.get('is_absent', False)
        
        # 欠勤の場合は出退勤時刻は不要
        if is_absent:
            return cleaned_data
        
        # 出勤時刻の検証
        if not clock_in:
            raise forms.ValidationError("出勤時刻を入力してください。")
        
        # 退勤時刻が入力されている場合の検証
        if clock_out and clock_out <= clock_in:
            raise forms.ValidationError("退勤時刻は出勤時刻より後である必要があります。")
        
        return cleaned_data
