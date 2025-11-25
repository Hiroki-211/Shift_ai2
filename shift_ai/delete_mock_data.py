"""
モックデータ（テストデータ）を削除するスクリプト

使い方:
    python delete_mock_data.py
"""

import os
import sys
import django

# Djangoの設定を読み込む
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shift_ai.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import Staff
from shift.models import Shift, ShiftRequest, ShiftSwapRequest, ShiftSwapApplication
from eval.models import Evaluation, AttendanceRecord

# 削除するモックデータのメールアドレス
MOCK_EMAILS = [
    'yamada@example.com',  # 花子 山田
    'sato@example.com',    # 次郎 佐藤
    'suzuki@example.com',  # 美咲 鈴木
    'tanaka@example.com',  # 健太 田中
    'test@example.com',    # ユーザー テスト
]


def delete_mock_data():
    """モックデータを削除"""
    print("\n" + "="*50)
    print("モックデータ削除開始")
    print("="*50 + "\n")
    
    deleted_count = 0
    
    for email in MOCK_EMAILS:
        try:
            user = User.objects.get(email=email)
            staff = Staff.objects.get(user=user)
            
            # 関連データを削除
            # シフト関連
            Shift.objects.filter(staff=staff).delete()
            ShiftRequest.objects.filter(staff=staff).delete()
            
            # シフト交代関連
            swap_requests = ShiftSwapRequest.objects.filter(requested_by=staff)
            for swap_request in swap_requests:
                ShiftSwapApplication.objects.filter(swap_request=swap_request).delete()
            swap_requests.delete()
            
            ShiftSwapApplication.objects.filter(applicant=staff).delete()
            
            # 評価・勤怠関連
            Evaluation.objects.filter(staff=staff).delete()
            Evaluation.objects.filter(evaluator=staff).delete()
            AttendanceRecord.objects.filter(staff=staff).delete()
            
            # スタッフとユーザーを削除
            staff_name = f"{staff.user.last_name} {staff.user.first_name}"
            staff.delete()
            user.delete()
            
            print(f"   ✓ 削除完了: {staff_name} ({email})")
            deleted_count += 1
            
        except User.DoesNotExist:
            print(f"   - スキップ: {email} (ユーザーが見つかりません)")
        except Staff.DoesNotExist:
            print(f"   - スキップ: {email} (スタッフ情報が見つかりません)")
        except Exception as e:
            print(f"   ✗ エラー: {email} - {str(e)}")
    
    print(f"\n   ✓ 削除完了: {deleted_count}件のモックデータを削除しました")
    print("\n" + "="*50)
    print("モックデータ削除完了")
    print("="*50 + "\n")


if __name__ == '__main__':
    try:
        # 確認メッセージ
        print("\n⚠️  警告: このスクリプトはモックデータを削除します！")
        print("削除対象:")
        for email in MOCK_EMAILS:
            print(f"  - {email}")
        
        # コマンドライン引数で確認をスキップ
        skip_confirm = len(sys.argv) > 1 and sys.argv[1] == '--yes'
        
        if not skip_confirm:
            response = input("\n続行しますか？ (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("\n処理をキャンセルしました。")
                sys.exit(0)
        
        delete_mock_data()
        print("\n✓ すべての処理が完了しました！\n")
    
    except KeyboardInterrupt:
        print("\n\n処理が中断されました。")
        sys.exit(1)
    except EOFError:
        # 対話的入力ができない場合は自動実行
        print("\n対話的入力ができないため、自動実行します...")
        delete_mock_data()
        print("\n✓ すべての処理が完了しました！\n")
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

