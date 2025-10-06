from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import Store, Staff


class Shift(models.Model):
    """シフトモデル"""
    store = models.ForeignKey(Store, on_delete=models.CASCADE, verbose_name="店舗")
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, verbose_name="スタッフ")
    date = models.DateField(verbose_name="勤務日")
    start_time = models.TimeField(verbose_name="開始時刻")
    end_time = models.TimeField(verbose_name="終了時刻")
    is_confirmed = models.BooleanField(default=False, verbose_name="確定フラグ")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "シフト"
        verbose_name_plural = "シフト"
        unique_together = ['staff', 'date', 'start_time']

    def __str__(self):
        return f"{self.staff.user.get_full_name()} - {self.date} {self.start_time}-{self.end_time}"

    @property
    def duration_hours(self):
        """勤務時間を計算"""
        from datetime import datetime, timedelta
        start_datetime = datetime.combine(self.date, self.start_time)
        end_datetime = datetime.combine(self.date, self.end_time)
        if end_datetime <= start_datetime:
            end_datetime += timedelta(days=1)
        return (end_datetime - start_datetime).total_seconds() / 3600

    @property
    def wage_cost(self):
        """人件費を計算"""
        return self.duration_hours * self.staff.hourly_wage


class ShiftRequest(models.Model):
    """希望シフトモデル"""
    REQUEST_TYPE_CHOICES = [
        ('off', '休み希望'),
        ('work', '勤務希望'),
    ]

    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, verbose_name="スタッフ")
    date = models.DateField(verbose_name="希望日")
    request_type = models.CharField(
        max_length=20, 
        choices=REQUEST_TYPE_CHOICES, 
        verbose_name="種別"
    )
    start_time = models.TimeField(null=True, blank=True, verbose_name="希望開始時刻")
    end_time = models.TimeField(null=True, blank=True, verbose_name="希望終了時刻")
    is_locked = models.BooleanField(default=False, verbose_name="編集ロック")
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "希望シフト"
        verbose_name_plural = "希望シフト"
        unique_together = ['staff', 'date', 'request_type']

    def __str__(self):
        return f"{self.staff.user.get_full_name()} - {self.date} ({self.get_request_type_display()})"
