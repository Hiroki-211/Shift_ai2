from django.urls import path
from . import staff_views

app_name = 'staff_eval'

urlpatterns = [
    # スタッフ評価機能
    path('evaluation/', staff_views.staff_evaluation_view, name='evaluation_view'),
]
