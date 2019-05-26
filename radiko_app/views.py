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

def index(request):
    return redirect('station/')

def mpd_play(content):
    logger = logging.getLogger('radio.debug')
    logger.info('Request MPD to play {}'.format(content))
    proc = subprocess.Popen(
        'mpc clear', shell=True, 
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    ret = proc.communicate()
    logger.debug(ret)
    proc = subprocess.Popen(
        'mpc add', shell=True, 
        stdin=subprocess.PIPE, 
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    ret = proc.communicate(content)
    logger.debug(ret)
    proc = subprocess.Popen(
        'mpc play', shell=True, 
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    ret = proc.communicate()
    logger.debug(ret)

def mpd_status():
    ret = subprocess.check_output(
        "mpc -f '%file%'", shell = True
    ).decode('utf-8').split("\n")[:3]
    try:
        content = ret[0]
        r = re.compile(
            '\[(.+)\]\s+#([0-9]+)/([0-9]+)\s+([0-9:]+)/([0-9:]+)\s+\([0-9]+%\)'
        )
        stat, n, nt, ct, tt = r.match(ret[1]).groups()
        k = [1, 60, 3600, 86400]
        t = 0 
        for i, s in enumerate(ct.split(':')[::-1]): 
            t += k[i] * int(s)
        return content, stat, t
    except:
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
                mpd_play(url.encode())
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

class ListProgram(LoginRequiredMixin, View):

    def render_(self, request, station_id):
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
        return render(request, 'radiko_app/program.html', d)

    def get(self, request, station_id):
        
        return self.render_(request, station_id)

    def post(self, request, station_id):
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
                ).format(settings.BASE_URL, station, ft, to, seek).encode()
                mpd_play(url)
                d = {'play':{
                    'id': p_id,
                    'station_id': station_id, 
                    'ft': ft, 
                    'to': to, 
                    'dur': dur, 
                    'seek': seek,
                    'title': title,
                    'from': t_from,
                    'url': url.decode()
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

