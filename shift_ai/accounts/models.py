from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Store(models.Model):
    """店舗モデル"""
    name = models.CharField(max_length=100, verbose_name="店舗名")
    opening_time = models.TimeField(verbose_name="開店時刻")
    closing_time = models.TimeField(verbose_name="閉店時刻")
    preparation_minutes = models.IntegerField(default=60, verbose_name="準備時間（分）")
    cleanup_minutes = models.IntegerField(default=60, verbose_name="片付け時間（分）")
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
    store = models.ForeignKey(Store, on_delete=models.CASCADE, verbose_name="店舗")
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
        return f"{self.user.get_full_name()} ({self.store.name})"


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
