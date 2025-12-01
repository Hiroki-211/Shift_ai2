from django import forms
from .models import ShiftSettings, ChatMessage


class ShiftSettingsForm(forms.ModelForm):
    """シフト設定フォーム"""
    
    class Meta:
        model = ShiftSettings
        fields = [
            'weekday_min_staff', 'weekday_max_staff',
            'weekend_min_staff', 'weekend_max_staff',
            'service_hours_min_staff', 'service_hours_max_staff',
            'after_last_order_min_staff', 'after_last_order_max_staff',
            'lunch_time_min_staff', 'lunch_time_max_staff',
            'dinner_time_min_staff', 'dinner_time_max_staff',
        ]
        widgets = {
            'weekday_min_staff': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 20}),
            'weekday_max_staff': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 20}),
            'weekend_min_staff': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 20}),
            'weekend_max_staff': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 20}),
            'service_hours_min_staff': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 20}),
            'service_hours_max_staff': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 20}),
            'after_last_order_min_staff': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 20}),
            'after_last_order_max_staff': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 20}),
            'lunch_time_min_staff': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 20}),
            'lunch_time_max_staff': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 20}),
            'dinner_time_min_staff': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 20}),
            'dinner_time_max_staff': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 20}),
        }
        labels = {
            'weekday_min_staff': '平日最小人数',
            'weekday_max_staff': '平日最大人数',
            'weekend_min_st_staff': '休日最小人数',
            'weekend_max_staff': '休日最大人数',
            'service_hours_min_staff': '営業時間中最小人数',
            'service_hours_max_staff': '営業時間中最大人数',
            'after_last_order_min_staff': 'ラストオーダー後最小人数',
            'after_last_order_max_staff': 'ラストオーダー後最大人数',
            'lunch_time_min_staff': 'ランチタイム中最小人数',
            'lunch_time_max_staff': 'ランチタイム中最大人数',
            'dinner_time_min_staff': 'ディナータイム中最小人数',
            'dinner_time_max_staff': 'ディナータイム中最大人数',
        }

    def clean(self):
        cleaned_data = super().clean()
        
        # 最小人数が最大人数を超えないようにチェック
        weekday_min = cleaned_data.get('weekday_min_staff')
        weekday_max = cleaned_data.get('weekday_max_staff')
        if weekday_min and weekday_max and weekday_min > weekday_max:
            raise forms.ValidationError('平日の最小人数は最大人数以下である必要があります。')
        
        weekend_min = cleaned_data.get('weekend_min_staff')
        weekend_max = cleaned_data.get('weekend_max_staff')
        if weekend_min and weekend_max and weekend_min > weekend_max:
            raise forms.ValidationError('休日の最小人数は最大人数以下である必要があります。')
        
        service_min = cleaned_data.get('service_hours_min_staff')
        service_max = cleaned_data.get('service_hours_max_staff')
        if service_min and service_max and service_min > service_max:
            raise forms.ValidationError('営業時間中の最小人数は最大人数以下である必要があります。')
        
        after_min = cleaned_data.get('after_last_order_min_staff')
        after_max = cleaned_data.get('after_last_order_max_staff')
        if after_min and after_max and after_min > after_max:
            raise forms.ValidationError('ラストオーダー後の最小人数は最大人数以下である必要があります。')
        
        lunch_min = cleaned_data.get('lunch_time_min_staff')
        lunch_max = cleaned_data.get('lunch_time_max_staff')
        if lunch_min and lunch_max and lunch_min > lunch_max:
            raise forms.ValidationError('ランチタイム中の最小人数は最大人数以下である必要があります。')
        
        dinner_min = cleaned_data.get('dinner_time_min_staff')
        dinner_max = cleaned_data.get('dinner_time_max_staff')
        if dinner_min and dinner_max and dinner_min > dinner_max:
            raise forms.ValidationError('ディナータイム中の最小人数は最大人数以下である必要があります。')
        
        return cleaned_data


class ChatMessageForm(forms.ModelForm):
    """チャットメッセージフォーム"""
    
    class Meta:
        model = ChatMessage
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'メッセージを入力してください...',
                'id': 'messageInput'
            })
        }
    
    def clean_message(self):
        message = self.cleaned_data.get('message')
        if not message or not message.strip():
            raise forms.ValidationError("メッセージを入力してください。")
        if len(message) > 1000:
            raise forms.ValidationError("メッセージは1000文字以内で入力してください。")
        return message.strip()




