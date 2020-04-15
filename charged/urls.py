from django.urls import path

from . import views

app_name = 'charged'

urlpatterns = [
    path('demo/', views.DemoView.as_view(), name='demo'),
]
