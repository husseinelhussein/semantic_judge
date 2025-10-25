from django.urls import path
from .views import JudgeView, BulkJudgeView

urlpatterns = [
    path('judge', JudgeView.as_view(), name='judge'),
    path('judge/bulk', BulkJudgeView.as_view(), name='judge_bulk'),
]
