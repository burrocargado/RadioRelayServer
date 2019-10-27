import urllib.request, urllib.error, urllib.parse
import os
import re
import subprocess
import signal
import base64
import json
from collections import OrderedDict
from datetime import datetime, timedelta
from http.cookiejar import FileCookieJar
import xml.etree.ElementTree as ET
import xmltodict

try:
    from . import radiko_auth_test as ra
except:
    from . import radiko_auth as ra

import logging

class Radiko():
    
    LOGIN_URL="https://radiko.jp/ap/member/login/login"
    CHECK_URL="https://radiko.jp/ap/member/webapi/member/login/check"
    LOGOUT_URL="https://radiko.jp/ap/member/webapi/member/logout"
    CHANNEL_AREA_URL="http://radiko.jp/v3/station/list/{}.xml"
    CHANNEL_FULL_URL="http://radiko.jp/v3/station/region/full.xml"
    PROG_NOW_URL = "http://radiko.jp/v3/program/now/{}.xml"
    PROG_TIMEFREE_URL = "http://radiko.jp/v3/program/date/{}/{}.xml"
    PROG_WEEKLY_URL = "http://radiko.jp/v3/program/station/weekly/{}.xml"
    
    LIVE_URL = (
        'http://f-radiko.smartstream.ne.jp/{}' 
        '/_definst_/simul-stream.stream/playlist.m3u8'
    )
    TIMEFREE_URL = (
        'https://radiko.jp/v2/api/ts/playlist.m3u8'
        '?station_id={0}'
        '&start_at={1}&ft={1}&end_at={2}&to={2}'
        '&l=15'
        '&type=b'
    )
    area_data = {}
    station_data = None
    stations = None
    token = None
    area = None
    inst_ctr = 0
    opener = None
    
    def __init__(
        self, acct={}, playlist={}, force_get_stations=False, logger=None):
        Radiko.inst_ctr += 1
        default_logger = logging.getLogger(__name__)
        default_logger.addHandler(logging.NullHandler)
        self.logger = logger or default_logger
        self.logger.debug('Radiko constructor: {}'.format(Radiko.inst_ctr))
        self.login_state = False
        if Radiko.opener:
            opener = Radiko.opener
            if acct:
                self.login_state = self.check_login(opener)
                if not self.login_state:
                    self.login(acct, opener)
                    self.login_state = self.check_login(opener)

        else:
            cj = FileCookieJar()
            opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(cj)
            )
            Radiko.opener = opener
            urllib.request.install_opener(opener)
            if acct:
                self.login(acct, opener)
                self.login_state = self.check_login(opener)

        if force_get_stations or not Radiko.area:
            token, area_id = self.get_token(trial=0)
            self.logger.info('getting stations')
            self.get_stations()
            if playlist:
                self.gen_playlist(
                    playlist['url'],
                    playlist['file']
                )

    def get_token(self, trial=0):
        
        return ra.get_token(trial=trial, rdk=self, logger=self.logger)

    def login(self, acct, opener):
        post = {
            'mail': acct['mail'],
            'pass': acct['pass']
        }
        data = urllib.parse.urlencode(post).encode('utf-8')
        res = opener.open(Radiko.LOGIN_URL, data)
        self.logger.debug('premium login tried')

    def check_login(self, opener):
        if not opener:
            self.logger.info('premium account not set')
            return None
        try:
            check = opener.open(Radiko.CHECK_URL)
            txt = check.read()
            self.logger.info('premium logged in')
            self.logger.debug(txt.decode())
            return json.loads(txt.decode())
        except urllib.request.HTTPError as e:
            self.logger.debug(e)
            if e.code == 400:
                self.logger.info('premium not logged in')
                return None
            else:
                raise e

    def logout(self):
        if self.login_state:
            logout = self.opener.open(Radiko.LOGOUT_URL)
            txt = logout.read()
            self.login_state = None
            self.logger.info('premium logout')
            return json.loads(txt.decode())

    def play(self, station, timefree={}):
        self.logger.info('playing {}'.format(station))
        if station not in self.stations:
            self.logger.error('{} not in available stations'.format(station))
            return
        self.current_station = station
            
        if timefree:
            ft = timefree['ft']
            to = timefree['to']
            if 'seek' not in timefree:
                seek_str = ft
                seek_opt = ''
                url = Radiko.TIMEFREE_URL.format(
                    station, ft, to
                )
            else:
                seek = int(timefree['seek'])
                t1 = datetime.strptime(ft, '%Y%m%d%H%M%S')
                t2 = t1 + timedelta(seconds=seek)
                seek_str = t2.strftime('%Y%m%d%H%M%S')
                url = Radiko.TIMEFREE_URL.format(
                    station, seek_str, to
                )
        else:
            url = Radiko.LIVE_URL.format(station)
            seek_opt = ''
        self.logger.debug('getting: ' + url)
        token, area_id = self.get_token(trial=1)
        if timefree:
            fdsink_opt = 'ts-offset=-15000000000 sync=true'
        else:
            fdsink_opt = 'sync=false'
        cmd = (
            "gst-launch-1.0 "
            "souphttpsrc location=\"{0}\" "
            "extra-headers=\"extra-headers, X-Radiko-AuthToken=(string){2};\" "
            "is-live=true "
            "! hlsdemux ! audio/mpeg "
            "! aacparse "
            "! fdsink {1}"
        ).format(url, fdsink_opt, token)
        
        self.logger.debug('cmd: ' + cmd)
        proc = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        pgid = os.getpgid(proc.pid)
        self.logger.debug('started subprocess: group id {}'
            .format(pgid))
        try:
            while True:
                out = proc.stdout.read(512)
                ret = proc.poll()
                if ret is not None:
                    self.logger.error(
                        'subprocess terminated: {}, return: {}'.format(station, ret)
                    )
                    break
                if out:
                    yield out
        finally:
            self.logger.info('stop playing {}'.format(station))
            if proc.poll() is None:
                self.logger.debug(
                    'killing process group {}'.format(pgid)
                )
                os.killpg(pgid, signal.SIGTERM)
                proc.wait()

    def download(self, station, outfile, timefree={}, liverec={}):
        self.logger.info('downloading {}'.format(station))
        if station not in self.stations:
            self.logger.error('{} not in available stations'.format(station))
            return
        self.current_station = station

        if timefree:
            ft = timefree['ft']
            to = timefree['to']
            url = Radiko.TIMEFREE_URL.format(
                station, ft, to
            )
        elif liverec:
            url = Radiko.LIVE_URL.format(station)
        else:
            return
        token, area_id = self.get_token(trial=1)
        if timefree:
            cmd = (
                "gst-launch-1.0 "
                "souphttpsrc location=\"{0}\" "
                "extra-headers=\"extra-headers, X-Radiko-AuthToken=(string){2};\" "
                "is-live=true "
                "! hlsdemux ! audio/mpeg "
                "! aacparse "
                "! filesink location=\"{1}\" "
            ).format(url, outfile, token)
        elif liverec:
            cmd = (
                "("
                "gst-launch-1.0 "
                "souphttpsrc location=\"{0}\" "
                "extra-headers=\"extra-headers, X-Radiko-AuthToken=(string){3};\" "
                "is-live=true "
                "! hlsdemux ! audio/mpeg "
                "! aacparse "
                "! filesink location=\"{1}\" "
                ") "
                "& sleep {2} ; ps $! > /dev/null 2>&1 && kill $!"
            ).format(url, outfile, liverec['duration'], token)

        proc = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, preexec_fn=os.setsid
        )
        proc.wait()

    def get_stations(self):
        res = urllib.request.urlopen(Radiko.CHANNEL_FULL_URL)
        xml_string = res.read()
        root = ET.fromstring(xml_string)
        station_data = []
        token_, area_id_ = self.get_token()
        for region in root:
            data = {}
            data['region'] = region.attrib
            data['stations'] = []
            for station in region:
                current_station = {}
                for e in station:
                    if e.tag in ['id', 'name', 
                        'ascii_name', 'areafree', 'timefree', 'area_id']:
                        value = e.itertext().__next__()
                        current_station[e.tag] = value
                data['stations'].append(current_station)
            station_data.append(data)
        Radiko.station_data = station_data
        areas = ['JP{}'.format(i+1) for i in range(47)]
        for area_id in areas:
            if area_id == area_id_ or area_id not in Radiko.area_data:
                res = urllib.request.urlopen(
                    Radiko.CHANNEL_AREA_URL.format(area_id))
                xml_string = res.read()
                root = ET.fromstring(xml_string)
                area_name = root.attrib['area_name']
                stations = []
                for station in root:
                    for e in station:
                        if e.tag in ['id']:
                            stations.append(e.itertext().__next__())
                Radiko.area_data[area_id] = {
                    'area_name':area_name, 
                    'stations':stations
                }
        stations = OrderedDict()
        for region in station_data:
            region_data = region['region']
            for s in region['stations']:
                station_id = s['id']
                region_name = region_data['region_name']
                area_id = s['area_id']
                area_name = re.sub(
                    '([^ ]+) JAPAN', '\\1', 
                    Radiko.area_data[area_id]['area_name']
                )
                name = s['name']
                if (self.login_state or 
                    station_id in Radiko.area_data[area_id_]['stations']):
                    stations[station_id] = (
                        name, region_name, area_id, area_name
                    )
        Radiko.stations = stations

    def gen_playlist(self, url_template, outfile):
        self.logger.info('writing playlist: {}'.format(outfile))
        with open(outfile, 'w') as f:
            f.write('#EXTM3U\n')
            f.write('\n')
            url = url_template
            for (
                    station_id, 
                    (name, region_name, area_id, area_name)
                ) in Radiko.stations.items():
                station_str = '{} / {}'.format(area_name.capitalize(), name)
                f.write('#EXTINF:-1,{}\n'.format(station_str))
                f.write(url.format(station_id)+'\n')
    
    def get_program(self, date_str, region_id):
        res = urllib.request.urlopen(
            Radiko.PROG_TIMEFREE_URL.format(date_str, region_id)
        )
        program = xmltodict.parse(res.read())
        return program
    
    def get_program_w(self, station):
        try:
            res = urllib.request.urlopen(
                Radiko.PROG_WEEKLY_URL.format(station)
            )
        except:
            self.logger.error('Error getting program: {}'.format(station))
            return {}
        program = xmltodict.parse(res.read())
        return program

    def __del__(self):
        Radiko.inst_ctr -= 1
        self.logger.debug('Radiko destructor: {}'.format(Radiko.inst_ctr))
        if Radiko.inst_ctr == 0:
            ret = self.logout()
            if ret:
                self.logger.debug(ret)

