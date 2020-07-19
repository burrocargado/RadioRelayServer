import urllib.request
import base64

AUTH1_URL="https://radiko.jp/v2/api/auth1"
AUTH2_URL="https://radiko.jp/v2/api/auth2"
AUTH_KEY = "bcd151073c03b352e1ef2fd66c32209da9ca0afa"

class RadikoAuth():
    def __init__(self, parent):
        self.parent = parent
        self.logger = parent.logger
        
    def get_token(self, trial=0):
        rdk = self.parent
        token = rdk.token
        area = rdk.area
        if not trial and token and area:
            return token, area

        self.logger.debug('radiko_auth')
        self.logger.debug(rdk.login_state)
        res = self.auth1()
        partialkey, token = self.get_partial_key(res)
        txt = self.auth2(partialkey, token)
        area_id, area_name, area_name_ascii = txt.strip().split(',')
        rdk.token = token
        rdk.area = area_id
        
        return token, area_id
    
    @staticmethod
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

    @staticmethod
    def get_partial_key(auth_response):

        authtoken = auth_response["headers"]["x-radiko-authtoken"]
        offset    = auth_response["headers"]["x-radiko-keyoffset"]
        length    = auth_response["headers"]["x-radiko-keylength"]

        offset = int(offset)
        length = int(length)
        partialkey= AUTH_KEY[offset:offset+length]
        partialkey = base64.b64encode(partialkey.encode())

        return partialkey, authtoken

    @staticmethod
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

