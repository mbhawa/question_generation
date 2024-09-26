from django.urls import path

from .views import generator_input_view, feedback_view, task_status_view


urlpatterns = [
    path('', generator_input_view, name='generator'),
    path('feedback/', feedback_view, name='feedback'),
    path('task-status/<str:task_id>/', task_status_view, name='task_status'),
]
