from django.urls import path

from . import views

app_name = 'radiko_app'
urlpatterns = [
    path('', views.index, name='index'),
    path('stream/<str:station_id>', views.Tune.as_view(), name='tune'),
    path('station/', views.ListStation.as_view(), name='station'),
    path('mpd/station/', views.ListStationMPD.as_view(), name='station_mpd'),
    path('stream/station/', views.ListStationStream.as_view(), name='station_stream'),
    path('status/', views.MPDStatus.as_view(), name='status'),
    path('program/<str:station_id>', views.ListProgram.as_view(), name='program'),
    path('mpd/program/<str:station_id>', views.ListProgram.as_view(), {'target': 'mpd'}, name='program_mpd'),
    path('stream/program/<str:station_id>', views.ListProgram.as_view(), {'target': 'stream'}, name='program_stream'),
]

