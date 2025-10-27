from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import random


class Store(models.Model):
    """店舗モデル"""
    name = models.CharField(max_length=100, verbose_name="店舗名")
    opening_time = models.TimeField(verbose_name="開店時刻")
    service_start_time = models.TimeField(verbose_name="営業開始時刻", null=True, blank=True)
    closing_time = models.TimeField(verbose_name="閉店時刻")
    last_order_time = models.TimeField(verbose_name="ラストオーダー時刻", null=True, blank=True)
    has_break_time = models.BooleanField(default=False, verbose_name="中休憩の有無")
    lunch_end_time = models.TimeField(verbose_name="ランチタイム終了時刻", null=True, blank=True)
    dinner_start_time = models.TimeField(verbose_name="ディナー営業開始時刻", null=True, blank=True)
    shift_submission_start_day = models.IntegerField(
        default=1, 
        verbose_name="シフト提出開始日",
        validators=[MinValueValidator(1), MaxValueValidator(28)],
        help_text="各月の何日からシフト提出が可能になるか（1-28日）"
    )
    shift_submission_deadline_day = models.IntegerField(
        default=20,
        verbose_name="シフト提出締切日",
        validators=[MinValueValidator(1), MaxValueValidator(28)],
        help_text="各月の何日までシフト提出が可能か（1-28日）"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "店舗"
        verbose_name_plural = "店舗"

    def __str__(self):
        return self.name


class Staff(models.Model):
    """スタッフモデル"""
    EMPLOYMENT_TYPE_CHOICES = [
        ('fixed', '固定勤務'),
        ('flexible', 'フレキシブル勤務'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="ユーザー")
    employee_id = models.CharField(max_length=20, unique=True, verbose_name="社員ID", blank=True)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, verbose_name="店舗")
    birth_date = models.DateField(verbose_name="生年月日", null=True, blank=True)
    employment_type = models.CharField(
        max_length=20, 
        choices=EMPLOYMENT_TYPE_CHOICES, 
        verbose_name="雇用形態"
    )
    hourly_wage = models.IntegerField(verbose_name="時給（円）")
    hall_skill_level = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="ホールスキル（1-5）"
    )
    kitchen_skill_level = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="キッチンスキル（1-5）"
    )
    is_manager = models.BooleanField(default=False, verbose_name="責任者フラグ")
    max_weekly_hours = models.IntegerField(default=40, verbose_name="週最大労働時間")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "スタッフ"
        verbose_name_plural = "スタッフ"

    def __str__(self):
        return f"{self.employee_id} - {self.user.get_full_name()} ({self.store.name})"
    
    @staticmethod
    def generate_employee_id():
        """重複しない6桁のランダムな社員番号を生成"""
        max_attempts = 100
        for _ in range(max_attempts):
            # 100000 から 999999 の範囲でランダムな番号を生成
            new_id = str(random.randint(100000, 999999))
            # 重複チェック（User.usernameとしても使用されるため、両方をチェック）
            from django.contrib.auth.models import User
            if not Staff.objects.filter(employee_id=new_id).exists() and not User.objects.filter(username=new_id).exists():
                return new_id
        # 100回試行しても重複しない番号が見つからない場合
        raise ValueError("社員番号の生成に失敗しました。既存の社員番号が多すぎます。")
    
    def save(self, *args, **kwargs):
        """社員IDを自動生成（6桁のランダムな数字）"""
        if not self.employee_id:
            self.employee_id = Staff.generate_employee_id()
        
        super().save(*args, **kwargs)


class StaffRequirement(models.Model):
    """必要人数設定モデル"""
    DAY_OF_WEEK_CHOICES = [
        (0, '月曜日'),
        (1, '火曜日'),
        (2, '水曜日'),
        (3, '木曜日'),
        (4, '金曜日'),
        (5, '土曜日'),
        (6, '日曜日'),
    ]

    store = models.ForeignKey(Store, on_delete=models.CASCADE, verbose_name="店舗")
    day_of_week = models.IntegerField(choices=DAY_OF_WEEK_CHOICES, verbose_name="曜日")
    start_time = models.TimeField(verbose_name="開始時刻")
    end_time = models.TimeField(verbose_name="終了時刻")
    required_staff = models.IntegerField(verbose_name="必要人数")
    required_managers = models.IntegerField(default=1, verbose_name="必要責任者数")
    required_hall_skill = models.IntegerField(default=0, verbose_name="必要ホールスキル人数")
    required_kitchen_skill = models.IntegerField(default=0, verbose_name="必要キッチンスキル人数")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "必要人数設定"
        verbose_name_plural = "必要人数設定"
        unique_together = ['store', 'day_of_week', 'start_time', 'end_time']

    def __str__(self):
        return f"{self.store.name} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"
