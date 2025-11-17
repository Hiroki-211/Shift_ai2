"""
管理者アカウント情報を表示するコマンド

使用方法:
    python manage.py show_admin_info

別のPCで管理者IDがわからない場合に使用します。
"""

from django.core.management.base import BaseCommand
from accounts.models import Staff


class Command(BaseCommand):
    help = '管理者アカウント情報を表示します'

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("管理者アカウント情報"))
        self.stdout.write("="*60 + "\n")
        
        # 管理者スタッフを取得
        admin_staff_list = Staff.objects.filter(is_manager=True).select_related('user', 'store')
        
        if not admin_staff_list.exists():
            self.stdout.write(self.style.WARNING("管理者アカウントが見つかりませんでした。"))
            self.stdout.write("\n管理者アカウントを作成するには、以下のコマンドを実行してください:")
            self.stdout.write("  python reset_database.py")
            self.stdout.write("  または")
            self.stdout.write("  python manage.py createsuperuser\n")
            return
        
        for admin_staff in admin_staff_list:
            self.stdout.write(f"【店舗】{admin_staff.store.name}")
            self.stdout.write(f"【管理者名】{admin_staff.user.get_full_name() or admin_staff.user.username}")
            self.stdout.write(f"【社員ID】{admin_staff.employee_id}")
            
            # パスワードは生年月日から生成されている場合がある
            if admin_staff.birth_date:
                password = admin_staff.birth_date.strftime('%Y%m%d')
                self.stdout.write(f"【パスワード（生年月日）】{password}")
            
            self.stdout.write(f"【メールアドレス】{admin_staff.user.email or '(未設定)'}")
            self.stdout.write(f"【ログインURL】http://127.0.0.1:8000/admin-login/")
            self.stdout.write("-" * 60)
        
        self.stdout.write("\n" + self.style.SUCCESS("✓ 表示完了\n"))

