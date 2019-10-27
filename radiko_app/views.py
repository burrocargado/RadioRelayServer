from django.views import View
from django.shortcuts import render
from django.http import HttpResponse, StreamingHttpResponse
from .models import Station, Program
from django.shortcuts import render, redirect
from django.utils.timezone import datetime, timedelta
#from django.utils import timezone
#from django.utils import html
#from django.urls import reverse
import subprocess
import re
import json
from . import radiko
from .tasks import download_program, record_program
from django.core import serializers

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin

import logging

from mpd import MPDClient

def index(request):
    return redirect('station/')

def mpd_play(content, title):
        client = MPDClient()
        client.connect(settings.MPD_ADDR, settings.MPD_PORT)
        client.clear()
        plid = client.addid(content)
        client.addtagid(plid, 'Title', title)
        client.playid(plid)

def mpd_status():
    client = MPDClient()
    client.connect(settings.MPD_ADDR, settings.MPD_PORT)
    status = client.status()
    current = client.currentsong()
    if 'elapsed' in status:
        stat = status['state']
        content = current['file']
        t = int(float(status['elapsed']))
        return content, stat, t
    else:
        return '', '', 0

class MPDStatus(View):
    def get(self, request):
        json_str = json.dumps(mpd_status())
        callback = request.GET.get('callback')
        if callback:
            json_str = "%s(%s)" % (callback, json_str)
            response = HttpResponse(
                json_str, 
                content_type='application/javascript; charset=UTF-8'
            )
        else:
            response = HttpResponse(
                json_str, 
                content_type='application/json; charset=UTF-8'
            )
        return response

class ListStation(LoginRequiredMixin, View):
    def get(self, request):
        logger = logging.getLogger('radio.debug')
        logger.debug(request)
        stations = Station.objects.all().order_by('station_no')
        d = {'stations': stations}
        return render(request, 'radiko_app/station.html', d)

    def post(self, request):
        logger = logging.getLogger('radio.debug')
        logger.debug(request)
        if request.method == 'POST':
            logger.debug(request.POST)
            station = request.POST['station_id']
            name = Station.objects.get(station_id=station).name
            if 'play' in request.POST:
                url = '{}/radiko/stream/{}'.format(settings.BASE_URL, station)
                mpd_play(url, name)
                response = HttpResponse(
                    'Playing on MPD<br><br>Live: {}'.format(name)
                )
                return response
            elif 'stream' in request.POST:
                d = {'play':{
                    'station_id': station, 
                    'name': name
                }}
                return render(request, 'radiko_app/play_live_stream.html', d)

class ListStationMPD(LoginRequiredMixin, View):
    def get(self, request):
        logger = logging.getLogger('radio.debug')
        logger.debug(request)
        stations = Station.objects.all().order_by('station_no')
        d = {'stations': stations}
        return render(request, 'radiko_app/station_mpd.html', d)

    def post(self, request):
        logger = logging.getLogger('radio.debug')
        logger.debug(request)
        if request.method == 'POST':
            logger.debug(request.POST)
            station = request.POST['station_id']
            name = Station.objects.get(station_id=station).name
            url = '{}/radiko/stream/{}'.format(settings.BASE_URL, station)
            mpd_play(url, name)
            response = HttpResponse(
                'Playing on MPD<br><br>Live: {}'.format(name)
            )
            return response

class ListStationStream(LoginRequiredMixin, View):
    def get(self, request):
        logger = logging.getLogger('radio.debug')
        logger.debug(request)
        stations = Station.objects.all().order_by('station_no')
        d = {'stations': stations}
        return render(request, 'radiko_app/station_stream.html', d)

    def post(self, request):
        logger = logging.getLogger('radio.debug')
        logger.debug(request)
        if request.method == 'POST':
            logger.debug(request.POST)
            station = request.POST['station_id']
            name = Station.objects.get(station_id=station).name
            d = {'play':{
                'station_id': station, 
                'name': name
            }}
            return render(request, 'radiko_app/play_live_stream.html', d)

class ListProgram(LoginRequiredMixin, View):

    def render_(self, request, station_id, kwargs):
        logger = logging.getLogger('radio.debug')
        logger.debug(request)
        logger.debug(station_id)
        s = Station.objects.filter(station_id=station_id)
        if s:
            name = s[0].name
        else:
            name = ''
        current = datetime.now().strftime('%Y%m%d%H%M%S')
        pgmp_ = Program.objects.filter(
            station_id=station_id
        ).filter(ft__lte=current).order_by('ft').reverse()
        pgmp = []
        for pgm in pgmp_:
            ft = datetime.strptime(pgm.ft, '%Y%m%d%H%M%S')
            pgmp.append({
                'id': pgm.id,
                'from': ft.strftime('%m/%d %H:%M'),
                'durm': '{:d}'.format(int(int(pgm.dur)/60)), 
                'title': pgm.title,
                'ft': pgm.ft,
                'to': pgm.to,
                'dur': pgm.dur,
                'download': pgm.download,
            })
        pgmf_ = Program.objects.filter(
            station_id=station_id
        ).filter(to__gt=current).order_by('ft').reverse()
        pgmf = []
        for pgm in pgmf_:
            ft = datetime.strptime(pgm.ft, '%Y%m%d%H%M%S')
            pgmf.append({
                'id': pgm.id,
                'from': ft.strftime('%m/%d %H:%M'),
                'durm': '{:d}'.format(int(int(pgm.dur)/60)), 
                'title': pgm.title,
                'ft': pgm.ft,
                'to': pgm.to,
                'dur': pgm.dur,
                'download': pgm.download,
            })
        d = {
            'station_id': station_id, 
            'name': name, 
            'programs_past': pgmp, 
            'programs_future': pgmf
        }
        if 'target' not in kwargs:
            return render(request, 'radiko_app/program.html', d)
        elif kwargs['target'] == 'mpd':
            return render(request, 'radiko_app/program_mpd.html', d)
        elif kwargs['target'] == 'stream':
            return render(request, 'radiko_app/program_stream.html', d)
        else:
            return render(request, 'radiko_app/program.html', d)

    def get(self, request, station_id, **kwargs):
        
        return self.render_(request, station_id, kwargs)

    def post(self, request, station_id, **kwargs):
        logger = logging.getLogger('radio.debug')
        logger.debug(request)
        if request.method == 'POST':
            logger.debug(request.POST)
            if 'downld' in request.POST:
                dllist = request.POST.getlist('chk_dl')
                for dl in dllist:
                    p_id = int(dl)
                    p = Program.objects.get(id=p_id)
                    logger.debug((p.title, p.ft))
                    download_program(p_id)
                    p.download = 1
                    p.save()
                response = HttpResponse('Download scheduled')
                return response

            if 'tmrec' in request.POST:
                dllist = request.POST.getlist('chk_tm')
                for dl in dllist:
                    p_id = int(dl)
                    p = Program.objects.get(id=p_id)
                    station = p.station_id
                    ft = p.ft
                    to = p.to
                    dur = p.dur
                    logger.debug((p.title, p.ft))
                    pgm_data = serializers.serialize(
                        "json", [p], ensure_ascii=False
                    )
                    params = {
                        'station_id': station, 
                        'ft': ft, 
                        'to': to, 
                        'dur': dur, 
                        'p_id': p_id, 
                        'data': pgm_data
                    }
                    rec_start = datetime.strptime(ft, '%Y%m%d%H%M%S')
                    record_program(params, schedule=rec_start)
                    p.download = 11
                    p.save()
                response = HttpResponse('Recording scheduled')
                return response

            p_id = request.POST['id']
            p = Program.objects.get(id=p_id)
            station = p.station_id
            ft = p.ft
            to = p.to
            dur = p.dur
            title = p.title
            start = datetime.strptime(ft, '%Y%m%d%H%M%S')
            t_from = start.strftime('%Y-%m-%d %H:%M')
            
            if 'seek' in request.POST:
                seek = request.POST['seek']
            else:
                seek = 0
            if 'play' in request.POST:
                url = (
                    '{0}/radiko/stream/{1}' 
                    '?ft={2}&to={3}&seek={4}'
                ).format(settings.BASE_URL, station, ft, to, seek)
                mpd_play(url, title)
                d = {'play':{
                    'id': p_id,
                    'station_id': station_id, 
                    'ft': ft, 
                    'to': to, 
                    'dur': dur, 
                    'seek': seek,
                    'title': title,
                    'from': t_from,
                    'url': url
                }}
                return render(request, 'radiko_app/play_tfree_mpd.html', d)
            elif 'stream' in request.POST:
                d = {'play':{
                    'id': p_id,
                    'station_id': station_id, 
                    'ft': ft, 
                    'to': to, 
                    'dur': dur, 
                    'seek': seek,
                    'title': title,
                    'from': t_from
                }}
                return render(request, 'radiko_app/play_tfree_stream.html', d)

class Tune(View):
    def get(self, request, station_id):
        logger = logging.getLogger('radio.debug')
        logger.debug(request)
        logger.debug(request.GET)
        if 'ft' in request.GET and 'to' in request.GET:
            timefree = {'ft': request.GET['ft'], 'to': request.GET['to']}
            if 'seek' in request.GET:
                timefree['seek'] = request.GET['seek']
        else:
            timefree = {}
        try:
            act = {'mail':settings.RADIKO_MAIL, 'pass':settings.RADIKO_PASS}
        except:
            act = {}
        rdk = radiko.Radiko(act, logger=logger)
        response = StreamingHttpResponse(
            rdk.play(station_id, timefree=timefree), content_type="audio/aac"
        )
        response['Cache-Control'] = 'no-cache, no-store'
        return response

