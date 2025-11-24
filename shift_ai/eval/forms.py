from django import forms
from .models import Evaluation, AttendanceRecord, EvaluationItem, EvaluationScore


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


class EvaluationItemForm(forms.ModelForm):
    """評価項目フォーム"""
    
    class Meta:
        model = EvaluationItem
        fields = ['name', 'description', 'max_score', 'order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '評価項目名を入力してください'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '評価項目の説明を入力してください（任意）'
            }),
            'max_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 100,
                'placeholder': '最大スコア'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'placeholder': '表示順序（小さい順）'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def clean_max_score(self):
        max_score = self.cleaned_data.get('max_score')
        if max_score < 1 or max_score > 100:
            raise forms.ValidationError("最大スコアは1から100の間で設定してください。")
        return max_score


class DynamicEvaluationForm(forms.Form):
    """動的評価フォーム（評価項目に基づいて生成）"""
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': '評価コメントを入力してください'
        })
    )
    
    def __init__(self, *args, **kwargs):
        evaluation_items = kwargs.pop('evaluation_items', [])
        evaluation = kwargs.pop('evaluation', None)
        super().__init__(*args, **kwargs)
        
        # コメントの初期値を設定
        if evaluation and evaluation.comment:
            self.fields['comment'].initial = evaluation.comment
        
        # 評価項目に基づいてフィールドを動的に生成
        for item in evaluation_items:
            field_name = f'item_{item.id}'
            initial_value = None
            
            # 既存の評価がある場合は、既存のスコアを取得
            if evaluation:
                try:
                    score_obj = EvaluationScore.objects.get(
                        evaluation=evaluation,
                        evaluation_item=item
                    )
                    initial_value = score_obj.score
                except EvaluationScore.DoesNotExist:
                    pass
            
            self.fields[field_name] = forms.IntegerField(
                label=item.name,
                required=True,
                min_value=0,
                max_value=item.max_score,
                initial=initial_value,
                widget=forms.NumberInput(attrs={
                    'class': 'form-control score-input',
                    'min': 0,
                    'max': item.max_score,
                    'placeholder': f'0-{item.max_score}点'
                }),
                help_text=item.description or f'最大{item.max_score}点'
            )
    
    def save(self, evaluation, evaluation_items):
        """評価スコアを保存"""
        # 評価スコアを保存
        for item in evaluation_items:
            field_name = f'item_{item.id}'
            score = self.cleaned_data.get(field_name, 0)
            
            EvaluationScore.objects.update_or_create(
                evaluation=evaluation,
                evaluation_item=item,
                defaults={'score': score}
            )
        
        # コメントを保存
        comment = self.cleaned_data.get('comment', '')
        evaluation.comment = comment
        evaluation.save()
