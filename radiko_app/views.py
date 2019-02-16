from django.views import View
from django.shortcuts import render
from django.http import HttpResponse, StreamingHttpResponse
from . import radiko
try:
    from settings import account
except:
    pass
from settings import config
import logging

def index(request):
    return HttpResponse("Hello, world. You're at the radiko_app index.")

class Tune(View):
    def get(self, request, station_id):
        logger = logging.getLogger('radio.debug')
        logger.debug(request)
        playlist = {
            'url': config.RADIKO_PLAYLIST_URL, 
            'file': config.RADIKO_PLAYLIST_FILE
        }
        try:
            act = {'mail':account.RADIKO_MAIL, 'pass':account.RADIKO_PASS}
        except:
            act = {}
        rdk = radiko.Radiko(act, playlist, logger=logger)
        response = StreamingHttpResponse(
            rdk.play(station_id), content_type="audio/aac"
        )
        response['Cache-Control'] = 'no-cache, no-store'
        logger.debug('get returning response')
        return response

