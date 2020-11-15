from . import radiko
from django.conf import settings

from .models import Station, Program
from background_task import background
from django.core import serializers
from django.utils import timezone
import logging
import os

@background(schedule=1, queue='timer_rec')
def record_program(params):
    logger=logging.getLogger('radio.debug')
    station_id = params['station_id']
    ft = params['ft']
    to = params['to']
    duration = params['dur']
    p_id = params['p_id']
    pgm_data = params['data']
    end = timezone.datetime.strptime(to, '%Y%m%d%H%M%S')
    dt = end - timezone.now()
    dt = dt.total_seconds()
    if dt < 0:
        return
    duration = int(dt)

    try:
        p = Program.objects.get(id=p_id)
        p.download = 12
        p.save()
    except:
        pass
    try:
        act = {'mail':settings.RADIKO_MAIL, 'pass':settings.RADIKO_PASS}
    except:
        act = {}
    rdk = radiko.Radiko(act, logger=logging.getLogger('radio.debug'))
    fbase = '{}_{}_{}_rec'.format(ft, to, station_id)
    path = settings.RADIKO_REC_DIR
    fpdata = os.path.join(path, '{}.json'.format(fbase))
    frec = os.path.join(path, '{}.aac'.format(fbase))
    logger.info('recording: {}'.format(frec))
    with open(fpdata, "w") as f:
        f.write(pgm_data)
    rdk.download(station_id, frec, liverec={'duration': duration})
    logger.info('recorded: {}'.format(frec))
    try:
        p.download = 13
        p.save()
    except:
        pass

@background(schedule=1, queue='download')
def download_program(p_id):
    logger=logging.getLogger('radio.debug')
    p = Program.objects.get(id=p_id)
    station_id = p.station_id
    ft = p.ft
    to = p.to
    p.download = 2
    p.save()
    try:
        act = {'mail':settings.RADIKO_MAIL, 'pass':settings.RADIKO_PASS}
    except:
        act = {}
    rdk = radiko.Radiko(act, logger=logging.getLogger('radio.debug'))
    fbase = '{}_{}_{}'.format(ft, to, station_id)
    path = settings.RADIKO_REC_DIR
    fpdata = os.path.join(path, '{}.json'.format(fbase))
    frec = os.path.join(path, '{}.aac'.format(fbase))    
    pgm_data = serializers.serialize("json", [p], ensure_ascii=False)
    logger.info('download: {}'.format(frec))
    with open(fpdata, "w") as f:
        f.write(pgm_data)
    rdk.download(p.station_id, frec, timefree={'ft': ft, 'to': to})
    logger.info('downloaded: {}'.format(frec))
    p.download = 3
    p.save()
    pgm_data = serializers.serialize("json", [p], ensure_ascii=False)
    with open(fpdata, "w") as f:
        f.write(pgm_data)

@background(schedule=1, queue='update-program')
def update_program(station):
    logger=logging.getLogger('radio.debug')
    logger.info('update_program: {}'.format(station))
    keys_db = [
        'prog_id', 'station_id', 'station_name', 'date',
        'title', 'failed_record', 'desc',
        'info', 'pfm', 'ft', 'to', 'dur']
    try:
        act = {'mail':account.RADIKO_MAIL, 'pass':account.RADIKO_PASS}
    except:
        act = {}
    rdk = radiko.Radiko(act, logger=logger)
    program = rdk.get_program_w(station)
    if not program:
        return
    data = program['radiko']['stations']['station']
    old_data = Program.objects.filter(station_id=station)
    rec_n = [] # new records
    rec_m = [] # modified records
    keys_u = [] # keys require update
    valid_id = []
    for d in data['progs']:
        date = d['date']
        for p in d['prog']:
            values={
                'prog_id': p['@id'],
                "station_id": station,
                "station_name": data['name'],
                "date": d['date'],
                "title": p['title'],
                "failed_record": p['failed_record'],
                "desc": p['desc'],
                "info": p['info'],
                "pfm": p['pfm'],
                "ft": p['@ft'],
                "to": p['@to'],
                "dur": p['@dur']
            }
            try:
                rec = old_data.get(ft=p['@ft'])
                valid_id.append(rec.id)
                keys_m = []
                for key in keys_db:
                    if values[key] != getattr(rec, key):
                        setattr(rec, key, values[key])
                        keys_m.append(key)
                if keys_m:
                    rec_m.append(rec)
                    for km in keys_m:
                        if km not in keys_u:
                            keys_u.append(km)
            except Program.DoesNotExist:
                rec = Program()
                for key in keys_db:
                    setattr(rec, key, values[key])
                setattr(rec, 'download', 0)
                rec_n.append(rec)
            except Program.MultipleObjectsReturned:
                # This should not happen.
                old_data.filter(ft=p['@ft']).delete()
                rec = Program()
                for key in keys_db:
                    setattr(rec, key, values[key])
                setattr(rec, 'download', 0)
                rec_n.append(rec)
    if rec_m:
        Program.objects.bulk_update(rec_m, fields=keys_u)
    Program.objects.filter(station_id=station).exclude(id__in=valid_id).delete()
    if rec_n:
        Program.objects.bulk_create(rec_n)

