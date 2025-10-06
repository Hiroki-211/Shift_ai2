from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Store, Staff, StaffRequirement


class StoreForm(forms.ModelForm):
    """店舗設定フォーム"""
    
    class Meta:
        model = Store
        fields = ['name', 'opening_time', 'closing_time', 'preparation_minutes', 'cleanup_minutes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'opening_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'closing_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'preparation_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
            'cleanup_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class StaffForm(forms.ModelForm):
    """スタッフ編集フォーム"""
    
    class Meta:
        model = Staff
        fields = [
            'employment_type', 'hourly_wage', 'hall_skill_level', 
            'kitchen_skill_level', 'is_manager', 'max_weekly_hours'
        ]
        widgets = {
            'employment_type': forms.Select(attrs={'class': 'form-control'}),
            'hourly_wage': forms.NumberInput(attrs={'class': 'form-control'}),
            'hall_skill_level': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'kitchen_skill_level': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'is_manager': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'max_weekly_hours': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class StaffRequirementForm(forms.ModelForm):
    """必要人数設定フォーム"""
    
    class Meta:
        model = StaffRequirement
        fields = [
            'day_of_week', 'start_time', 'end_time', 'required_staff',
            'required_managers', 'required_hall_skill', 'required_kitchen_skill'
        ]
        widgets = {
            'day_of_week': forms.Select(attrs={'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'required_staff': forms.NumberInput(attrs={'class': 'form-control'}),
            'required_managers': forms.NumberInput(attrs={'class': 'form-control'}),
            'required_hall_skill': forms.NumberInput(attrs={'class': 'form-control'}),
            'required_kitchen_skill': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class UserRegistrationForm(UserCreationForm):
    """ユーザー登録フォーム"""
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user
