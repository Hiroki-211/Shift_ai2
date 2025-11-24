from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import Staff, Store


class Evaluation(models.Model):
    """評価モデル"""
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, verbose_name="スタッフ")
    evaluator = models.ForeignKey(
        Staff, 
        on_delete=models.CASCADE, 
        related_name='evaluations_given',
        verbose_name="評価者"
    )
    evaluation_period = models.CharField(max_length=20, verbose_name="評価期間（例：2025-09）")
    
    # 評価項目（仕様書に基づく配点）
    attendance_score = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(30)],
        verbose_name="勤怠スコア（0-30点）"
    )
    skill_score = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(40)],
        verbose_name="業務スキルスコア（0-40点）"
    )
    teamwork_score = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(20)],
        verbose_name="チームワークスコア（0-20点）"
    )
    customer_service_score = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        verbose_name="顧客対応スコア（0-10点）"
    )
    total_score = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="合計スコア（0-100点）"
    )
    comment = models.TextField(blank=True, null=True, verbose_name="コメント")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "評価"
        verbose_name_plural = "評価"
        unique_together = ['staff', 'evaluator', 'evaluation_period']

    def __str__(self):
        return f"{self.staff.user.get_full_name()} - {self.evaluation_period} ({self.total_score}点)"

    def save(self, *args, **kwargs):
        """合計スコアを自動計算"""
        self.total_score = (
            self.attendance_score + 
            self.skill_score + 
            self.teamwork_score + 
            self.customer_service_score
        )
        super().save(*args, **kwargs)


class EvaluationItem(models.Model):
    """評価項目モデル"""
    store = models.ForeignKey(Store, on_delete=models.CASCADE, verbose_name="店舗")
    name = models.CharField(max_length=100, verbose_name="評価項目名")
    description = models.TextField(blank=True, null=True, verbose_name="説明")
    max_score = models.IntegerField(
        default=100,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        verbose_name="最大スコア"
    )
    order = models.IntegerField(default=0, verbose_name="表示順序")
    is_active = models.BooleanField(default=True, verbose_name="有効")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "評価項目"
        verbose_name_plural = "評価項目"
        ordering = ['order', 'id']
        unique_together = ['store', 'name']

    def __str__(self):
        return f"{self.store.name} - {self.name} (最大{self.max_score}点)"


class EvaluationScore(models.Model):
    """評価スコアモデル（評価と評価項目の中間テーブル）"""
    evaluation = models.ForeignKey(
        Evaluation, 
        on_delete=models.CASCADE, 
        related_name='scores',
        verbose_name="評価"
    )
    evaluation_item = models.ForeignKey(
        EvaluationItem,
        on_delete=models.CASCADE,
        verbose_name="評価項目"
    )
    score = models.IntegerField(
        validators=[MinValueValidator(0)],
        verbose_name="スコア"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "評価スコア"
        verbose_name_plural = "評価スコア"
        unique_together = ['evaluation', 'evaluation_item']

    def __str__(self):
        return f"{self.evaluation} - {self.evaluation_item.name}: {self.score}点"


class AttendanceRecord(models.Model):
    """勤怠記録モデル"""
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, verbose_name="スタッフ")
    date = models.DateField(verbose_name="勤務日")
    clock_in = models.DateTimeField(verbose_name="出勤時刻")
    clock_out = models.DateTimeField(null=True, blank=True, verbose_name="退勤時刻")
    is_late = models.BooleanField(default=False, verbose_name="遅刻フラグ")
    is_early_leave = models.BooleanField(default=False, verbose_name="早退フラグ")
    is_absent = models.BooleanField(default=False, verbose_name="欠勤フラグ")
    notes = models.TextField(blank=True, null=True, verbose_name="備考")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "勤怠記録"
        verbose_name_plural = "勤怠記録"
        unique_together = ['staff', 'date']

    def __str__(self):
        return f"{self.staff.user.get_full_name()} - {self.date}"

    @property
    def work_hours(self):
        """勤務時間を計算"""
        if self.clock_out:
            return (self.clock_out - self.clock_in).total_seconds() / 3600
        return 0
