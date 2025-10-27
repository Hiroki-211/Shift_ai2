"""
データベースをリセットしてテストデータを作成するスクリプト

使い方:
    python reset_database.py
"""

import os
import sys
import django

# Djangoの設定を読み込む
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shift_ai.settings')
django.setup()

from django.contrib.auth.models import User
from django.core.management import call_command
from accounts.models import Store, Staff, StaffRequirement
from shift.models import Shift, ShiftRequest
from eval.models import Evaluation, AttendanceRecord
from datetime import datetime, date, time, timedelta


def reset_database():
    """データベースをリセット"""
    print("\n" + "="*50)
    print("データベースリセット開始")
    print("="*50 + "\n")
    
    # データベースの全データを削除
    print("1. データベースのデータを削除中...")
    call_command('flush', '--no-input')
    print("   ✓ データ削除完了\n")
    
    # マイグレーションを適用
    print("2. マイグレーションを適用中...")
    call_command('migrate', '--no-input')
    print("   ✓ マイグレーション完了\n")


def create_test_data():
    """テストデータを作成"""
    print("3. テストデータを作成中...")
    
    # 店舗を作成
    print("   - 店舗を作成中...")
    store = Store.objects.create(
        name='サンプルレストラン',
        opening_time=time(10, 0),
        closing_time=time(22, 0),
        preparation_minutes=30,
        cleanup_minutes=30
    )
    print(f"   ✓ 店舗作成: {store.name}")
    
    # 管理者ユーザーを作成
    print("   - 管理者ユーザーを作成中...")
    # 社員IDを先に生成
    admin_employee_id = Staff.generate_employee_id()
    # 社員IDをusernameとして使用
    admin_user = User.objects.create_user(
        username=admin_employee_id,
        email='admin@example.com',
        password='19900101',  # 生年月日形式
        first_name='管理',
        last_name='太郎'
    )
    admin_staff = Staff.objects.create(
        user=admin_user,
        store=store,
        employee_id=admin_employee_id,
        birth_date=date(1990, 1, 1),
        employment_type='fixed',
        hourly_wage=1500,
        is_manager=True,
        hall_skill_level=5,
        kitchen_skill_level=5,
        max_weekly_hours=40
    )
    print(f"   ✓ 管理者作成: 社員ID={admin_staff.employee_id} / password: 19900101")
    
    # スタッフユーザーを作成
    print("   - スタッフユーザーを作成中...")
    staff_data = [
        {
            'first_name': '山田',
            'last_name': '花子',
            'email': 'yamada@example.com',
            'birth_date': date(1995, 3, 15),
            'employment_type': 'fixed',
            'hourly_wage': 1300,
            'hall_skill': 4,
            'kitchen_skill': 3,
        },
        {
            'first_name': '佐藤',
            'last_name': '次郎',
            'email': 'sato@example.com',
            'birth_date': date(1998, 7, 22),
            'employment_type': 'flexible',
            'hourly_wage': 1200,
            'hall_skill': 3,
            'kitchen_skill': 4,
        },
        {
            'first_name': '鈴木',
            'last_name': '美咲',
            'email': 'suzuki@example.com',
            'birth_date': date(2000, 11, 8),
            'employment_type': 'flexible',
            'hourly_wage': 1100,
            'hall_skill': 3,
            'kitchen_skill': 2,
        },
        {
            'first_name': '田中',
            'last_name': '健太',
            'email': 'tanaka@example.com',
            'birth_date': date(1997, 5, 30),
            'employment_type': 'flexible',
            'hourly_wage': 1150,
            'hall_skill': 2,
            'kitchen_skill': 4,
        },
    ]
    
    staff_list = []
    for data in staff_data:
        # 社員IDを先に生成
        employee_id = Staff.generate_employee_id()
        # 生年月日からパスワードを生成
        password = data['birth_date'].strftime('%Y%m%d')
        
        # ユーザーを作成（社員IDをusernameとして使用）
        user = User.objects.create_user(
            username=employee_id,
            email=data['email'],
            password=password,
            first_name=data['first_name'],
            last_name=data['last_name']
        )
        staff = Staff.objects.create(
            user=user,
            store=store,
            employee_id=employee_id,
            birth_date=data['birth_date'],
            employment_type=data['employment_type'],
            hourly_wage=data['hourly_wage'],
            is_manager=False,
            hall_skill_level=data['hall_skill'],
            kitchen_skill_level=data['kitchen_skill'],
            max_weekly_hours=30
        )
        staff_list.append(staff)
        print(f"   ✓ スタッフ作成: {staff.user.get_full_name()} / 社員ID={employee_id} / password: {password}")
    
    # 必要人数設定を作成
    print("   - 必要人数設定を作成中...")
    requirements_data = [
        # 平日
        {'day': 1, 'start': '10:00', 'end': '14:00', 'staff': 3, 'managers': 1, 'hall': 2, 'kitchen': 1},
        {'day': 1, 'start': '14:00', 'end': '18:00', 'staff': 2, 'managers': 1, 'hall': 1, 'kitchen': 1},
        {'day': 1, 'start': '18:00', 'end': '22:00', 'staff': 4, 'managers': 1, 'hall': 2, 'kitchen': 2},
        # 土日
        {'day': 6, 'start': '10:00', 'end': '14:00', 'staff': 5, 'managers': 1, 'hall': 3, 'kitchen': 2},
        {'day': 6, 'start': '14:00', 'end': '18:00', 'staff': 4, 'managers': 1, 'hall': 2, 'kitchen': 2},
        {'day': 6, 'start': '18:00', 'end': '22:00', 'staff': 6, 'managers': 1, 'hall': 3, 'kitchen': 3},
    ]
    
    for req in requirements_data:
        StaffRequirement.objects.create(
            store=store,
            day_of_week=req['day'],
            start_time=req['start'],
            end_time=req['end'],
            required_staff=req['staff'],
            required_managers=req['managers'],
            required_hall_skill=req['hall'],
            required_kitchen_skill=req['kitchen']
        )
    print(f"   ✓ 必要人数設定作成: {len(requirements_data)}件")
    
    # サンプルシフト希望を作成（来月分）
    print("   - サンプルシフト希望を作成中...")
    today = date.today()
    if today.month == 12:
        next_month = date(today.year + 1, 1, 1)
    else:
        next_month = date(today.year, today.month + 1, 1)
    
    # 月末日を取得
    if next_month.month == 12:
        next_month_end = date(next_month.year + 1, 1, 1) - timedelta(days=1)
    else:
        next_month_end = date(next_month.year, next_month.month + 1, 1) - timedelta(days=1)
    
    request_count = 0
    for staff in staff_list:
        # ランダムに希望シフトを作成
        current_date = next_month
        while current_date <= next_month_end:
            # 3日に1回程度休み希望
            if current_date.day % 3 == 0:
                ShiftRequest.objects.create(
                    staff=staff,
                    date=current_date,
                    request_type='off',
                    start_time=None,
                    end_time=None
                )
                request_count += 1
            # それ以外は勤務希望
            elif current_date.day % 2 == 0:
                ShiftRequest.objects.create(
                    staff=staff,
                    date=current_date,
                    request_type='work',
                    start_time=time(10, 0),
                    end_time=time(18, 0)
                )
                request_count += 1
            
            current_date += timedelta(days=1)
    
    print(f"   ✓ シフト希望作成: {request_count}件")
    
    # サンプルシフトを作成（今月分）
    print("   - サンプルシフトを作成中...")
    month_start = today.replace(day=1)
    shift_count = 0
    
    for i in range(7):  # 今週のシフトを作成
        shift_date = month_start + timedelta(days=i)
        
        # 管理者のシフト
        Shift.objects.create(
            store=store,
            staff=admin_staff,
            date=shift_date,
            start_time=time(10, 0),
            end_time=time(18, 0),
            is_confirmed=True
        )
        shift_count += 1
        
        # スタッフのシフト
        for staff in staff_list[:2]:  # 最初の2人
            Shift.objects.create(
                store=store,
                staff=staff,
                date=shift_date,
                start_time=time(14, 0),
                end_time=time(22, 0),
                is_confirmed=True
            )
            shift_count += 1
    
    print(f"   ✓ シフト作成: {shift_count}件")
    
    print("\n" + "="*50)
    print("テストデータ作成完了！")
    print("="*50 + "\n")
    
    # ログイン情報を表示
    print("【ログイン情報】")
    print("\n管理者アカウント:")
    print("  URL: http://127.0.0.1:8000/admin-login/")
    print("  ユーザー名: admin")
    print("  パスワード: admin123")
    
    print("\nスタッフアカウント:")
    print("  URL: http://127.0.0.1:8000/staff-login/")
    for data in staff_data:
        print(f"  ユーザー名: {data['username']} / パスワード: {data['password']}")
    
    print("\n" + "="*50)


if __name__ == '__main__':
    try:
        # 確認メッセージ
        print("\n⚠️  警告: このスクリプトは既存のデータをすべて削除します！")
        response = input("続行しますか？ (yes/no): ")
        
        if response.lower() in ['yes', 'y']:
            reset_database()
            create_test_data()
            print("\n✓ すべての処理が完了しました！")
            print("サーバーを起動してログインしてください。\n")
        else:
            print("\n処理をキャンセルしました。")
    
    except KeyboardInterrupt:
        print("\n\n処理が中断されました。")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

