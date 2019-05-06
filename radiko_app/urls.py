from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('stream/<str:station_id>', views.Tune.as_view(), name='tune'),
    path('station/', views.ListStation.as_view(), name='station'),
    path('status/', views.MPDStatus.as_view(), name='status'),
    path('program/<str:station_id>', views.ListProgram.as_view(), name='program'),
]

