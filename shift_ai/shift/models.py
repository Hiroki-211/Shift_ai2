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
    end_date = models.DateField(null=True, blank=True, verbose_name="終了日")
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
        end_date = self.end_date if self.end_date else self.date
        end_datetime = datetime.combine(end_date, self.end_time)
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
    end_date = models.DateField(null=True, blank=True, verbose_name="終了日")
    is_locked = models.BooleanField(default=False, verbose_name="編集ロック")
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "希望シフト"
        verbose_name_plural = "希望シフト"
        unique_together = ['staff', 'date', 'request_type']

    def __str__(self):
        return f"{self.staff.user.get_full_name()} - {self.date} ({self.get_request_type_display()})"


class ShiftSettings(models.Model):
    """シフト設定モデル"""
    store = models.ForeignKey(Store, on_delete=models.CASCADE, verbose_name="店舗")
    
    # 平日・休日の基本人数
    weekday_min_staff = models.PositiveIntegerField(default=2, verbose_name="平日最小人数")
    weekday_max_staff = models.PositiveIntegerField(default=5, verbose_name="平日最大人数")
    weekend_min_staff = models.PositiveIntegerField(default=3, verbose_name="休日最小人数")
    weekend_max_staff = models.PositiveIntegerField(default=6, verbose_name="休日最大人数")
    
    # 営業時間中の人数
    service_hours_min_staff = models.PositiveIntegerField(default=3, verbose_name="営業時間中最小人数")
    service_hours_max_staff = models.PositiveIntegerField(default=6, verbose_name="営業時間中最大人数")
    
    # ラストオーダー後の人数
    after_last_order_min_staff = models.PositiveIntegerField(default=2, verbose_name="ラストオーダー後最小人数")
    after_last_order_max_staff = models.PositiveIntegerField(default=4, verbose_name="ラストオーダー後最大人数")
    
    # ランチタイム中の人数（中休憩がある場合）
    lunch_time_min_staff = models.PositiveIntegerField(default=2, verbose_name="ランチタイム中最小人数", null=True, blank=True)
    lunch_time_max_staff = models.PositiveIntegerField(default=4, verbose_name="ランチタイム中最大人数", null=True, blank=True)
    
    # ディナータイム中の人数
    dinner_time_min_staff = models.PositiveIntegerField(default=3, verbose_name="ディナータイム中最小人数")
    dinner_time_max_staff = models.PositiveIntegerField(default=6, verbose_name="ディナータイム中最大人数")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "シフト設定"
        verbose_name_plural = "シフト設定"
        unique_together = ['store']

    def __str__(self):
        return f"{self.store.name} - シフト設定"


class ShiftSwapRequest(models.Model):
    """シフト交代募集モデル"""
    STATUS_CHOICES = [
        ('open', '募集中'),
        ('closed', '締切'),
        ('completed', '完了'),
        ('cancelled', 'キャンセル'),
    ]
    
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, verbose_name="対象シフト")
    requested_by = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='swap_requests', verbose_name="募集者")
    date = models.DateField(verbose_name="交代希望日")
    start_time = models.TimeField(verbose_name="開始時刻")
    end_time = models.TimeField(verbose_name="終了時刻")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='open',
        verbose_name="状態"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")
    
    class Meta:
        verbose_name = "シフト交代募集"
        verbose_name_plural = "シフト交代募集"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.requested_by.user.get_full_name()} - {self.date} {self.start_time}-{self.end_time}"
    
    @property
    def is_available(self):
        """出勤日の1日前まで使用可能かどうか"""
        from datetime import date, timedelta
        deadline = self.date - timedelta(days=1)
        return date.today() <= deadline and self.status == 'open'
    
    @property
    def deadline(self):
        """締切日（出勤日の1日前）"""
        from datetime import timedelta
        return self.date - timedelta(days=1)


class ShiftSwapApplication(models.Model):
    """シフト交代立候補モデル"""
    STATUS_CHOICES = [
        ('pending', '待機中'),
        ('accepted', '承認済み'),
        ('rejected', '却下'),
        ('cancelled', 'キャンセル'),
    ]
    
    swap_request = models.ForeignKey(ShiftSwapRequest, on_delete=models.CASCADE, related_name='applications', verbose_name="シフト交代募集")
    applicant = models.ForeignKey(Staff, on_delete=models.CASCADE, verbose_name="立候補者")
    start_time = models.TimeField(verbose_name="希望開始時刻")
    end_time = models.TimeField(verbose_name="希望終了時刻")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="状態"
    )
    message = models.TextField(blank=True, verbose_name="メッセージ")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")
    
    class Meta:
        verbose_name = "シフト交代立候補"
        verbose_name_plural = "シフト交代立候補"
        unique_together = ['swap_request', 'applicant']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.applicant.user.get_full_name()} - {self.swap_request.date} {self.start_time}-{self.end_time}"


class ChatRoom(models.Model):
    """チャットルームモデル"""
    ROOM_TYPE_CHOICES = [
        ('staff_staff', 'スタッフ同士'),
        ('staff_manager', 'スタッフ-管理者'),
        ('swap_request', 'シフト交代関連'),
    ]
    
    store = models.ForeignKey(Store, on_delete=models.CASCADE, verbose_name="店舗")
    room_type = models.CharField(
        max_length=20,
        choices=ROOM_TYPE_CHOICES,
        default='staff_staff',
        verbose_name="ルームタイプ"
    )
    participant1 = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='chat_rooms_as_participant1',
        verbose_name="参加者1"
    )
    participant2 = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='chat_rooms_as_participant2',
        verbose_name="参加者2"
    )
    swap_request = models.ForeignKey(
        ShiftSwapRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_rooms',
        verbose_name="シフト交代申請"
    )
    swap_application = models.ForeignKey(
        ShiftSwapApplication,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_rooms',
        verbose_name="シフト交代立候補"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")
    
    class Meta:
        verbose_name = "チャットルーム"
        verbose_name_plural = "チャットルーム"
        unique_together = ['participant1', 'participant2', 'swap_request']
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.participant1.user.get_full_name()} - {self.participant2.user.get_full_name()}"
    
    def get_other_participant(self, current_staff):
        """現在のスタッフ以外の参加者を取得"""
        if self.participant1 == current_staff:
            return self.participant2
        return self.participant1
    
    def get_unread_count(self, staff):
        """未読メッセージ数を取得"""
        return self.messages.filter(is_read=False).exclude(sender=staff).count()
    
    @classmethod
    def get_or_create_room(cls, staff1, staff2, swap_request=None, swap_application=None):
        """チャットルームを取得または作成"""
        # 参加者の順序を統一（IDが小さい方をparticipant1に）
        if staff1.id > staff2.id:
            staff1, staff2 = staff2, staff1
        
        room_type = 'swap_request' if swap_request else ('staff_manager' if (staff1.is_manager or staff2.is_manager) else 'staff_staff')
        
        room, created = cls.objects.get_or_create(
            participant1=staff1,
            participant2=staff2,
            swap_request=swap_request,
            defaults={
                'store': staff1.store,
                'room_type': room_type,
                'swap_application': swap_application
            }
        )
        return room, created


class ChatMessage(models.Model):
    """チャットメッセージモデル"""
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name="チャットルーム"
    )
    sender = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        verbose_name="送信者"
    )
    message = models.TextField(verbose_name="メッセージ")
    is_read = models.BooleanField(default=False, verbose_name="既読")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="送信日時")
    
    class Meta:
        verbose_name = "チャットメッセージ"
        verbose_name_plural = "チャットメッセージ"
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.sender.user.get_full_name()} - {self.message[:50]}"
    
    def mark_as_read(self, reader):
        """メッセージを既読にする"""
        if self.sender != reader:
            self.is_read = True
            self.save()