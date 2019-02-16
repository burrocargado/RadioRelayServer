from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('<str:station_id>', views.Tune.as_view(), name='tune'),
]

