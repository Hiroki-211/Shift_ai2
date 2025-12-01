"""カスタム認証バックエンド"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from .models import Staff


class EmployeeIDBackend(ModelBackend):
    """社員IDでの認証バックエンド"""
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # 社員IDでStaffを検索
            staff = Staff.objects.get(employee_id=username)
            user = staff.user
            
            # パスワードをチェック
            if user.check_password(password):
                return user
        except Staff.DoesNotExist:
            # 社員IDが見つからない場合は通常のユーザー名で試す
            try:
                user = User.objects.get(username=username)
                if user.check_password(password):
                    return user
            except User.DoesNotExist:
                pass
        
        return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

