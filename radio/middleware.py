from radiko_app import radiko
from django.conf import settings
import os
import logging

from radiko_app.models import Station, Program
from background_task.models import Task
from radiko_app.tasks import update_program


class RadikoMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response
        #print('(1) init')

        radiko.Radiko.FFMPEG = os.path.join(settings.BASE_DIR, 'ffmpeg')
        playlist = {
            'url': settings.BASE_URL + '/radiko/stream/{}', 
            'file': settings.RADIKO_PLAYLIST_FILE
        }
        try:
            act = {'mail':settings.RADIKO_MAIL, 'pass':settings.RADIKO_PASS}
        except:
            act = {}
        rdk = radiko.Radiko(act, playlist, logger=logging.getLogger('radio.debug'))
        stations = rdk.stations
        Task.objects.filter(queue='update-program').delete()
        rec_n = []
        Station.objects.all().delete()
        for i, (station, (name, region, area, area_name)) in enumerate(stations.items()):
            rec = Station()
            rec.station_id = station
            rec.station_no = i + 1
            rec.name = name
            rec.area_id = area
            rec.area_name = area_name
            rec.region = region
            rec_n.append(rec)
            update_program(station, schedule=i*6, repeat=3600)
        Station.objects.bulk_create(rec_n)

    def __call__(self, request):
        #print('(2): before get_response')

        response = self.get_response(request)

        #print('(3): after get_response')

        return response



