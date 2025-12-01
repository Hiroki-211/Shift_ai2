from django import template

register = template.Library()


@register.filter
def japanese_name(user):
    """日本語形式の名前を取得（姓 名の順）"""
    if not user:
        return ''
    if user.last_name and user.first_name:
        return f"{user.last_name} {user.first_name}".strip()
    elif user.last_name:
        return user.last_name
    elif user.first_name:
        return user.first_name
    else:
        return user.username




