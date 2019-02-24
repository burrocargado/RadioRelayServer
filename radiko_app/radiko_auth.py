import urllib.request
import base64
from . import radiko

def get_token(rdk=None, logger=None):

    token = radiko.Radiko.token
    area = radiko.Radiko.area
    if token and area:
        return token, area
    
    AUTH1_URL="https://radiko.jp/v2/api/auth1"
    AUTH2_URL="https://radiko.jp/v2/api/auth2"
    AUTH_KEY = "bcd151073c03b352e1ef2fd66c32209da9ca0afa"

    if logger:
        logger.info('radiko_auth')
        logger.info(rdk.login_state)

    def auth1():
        auth_response = {}

        headers = {
                "User-Agent": "curl/7.56.1",
                "Accept": "*/*",
                "X-Radiko-App":"pc_html5" ,
                "X-Radiko-App-Version":"0.0.1" ,
                "X-Radiko-User":"dummy_user" ,
                "X-Radiko-Device":"pc" ,
        }
        req  = urllib.request.Request( AUTH1_URL, None, headers  )
        res  = urllib.request.urlopen(req)
        auth_response["body"] = res.read()
        auth_response["headers"] = res.info()

        return auth_response


    def get_partial_key(auth_response):

        authtoken = auth_response["headers"]["x-radiko-authtoken"]
        offset    = auth_response["headers"]["x-radiko-keyoffset"]
        length    = auth_response["headers"]["x-radiko-keylength"]

        offset = int(offset)
        length = int(length)
        partialkey= AUTH_KEY[offset:offset+length]
        partialkey = base64.b64encode(partialkey.encode())

        return partialkey, authtoken


    def auth2(partialkey, auth_token) :

        headers =  {
            "X-Radiko-AuthToken": auth_token,
            "X-Radiko-Partialkey": partialkey,
            "X-Radiko-User": "dummy_user",
            "X-Radiko-Device": 'pc'
        }

        req  = urllib.request.Request(AUTH2_URL, None, headers)
        res  = urllib.request.urlopen(req)
        text = res.read().decode()

        return text

    res = auth1()
    partialkey, token = get_partial_key(res)
    txt = auth2(partialkey, token)
    area_id, area_name, area_name_ascii = txt.strip().split(',')

    return token, area_id

