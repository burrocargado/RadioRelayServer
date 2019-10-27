import os
import json
from django.contrib.auth.hashers import make_password
import string
import secrets

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'radio.settings')

def pass_gen(size=12):
   chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
   return ''.join(secrets.choice(chars) for x in range(size))

raw_pw = pass_gen()
pw = make_password(raw_pw)

data =  [
    { "model": "auth.user",
        "pk": 1,
        "fields": {
            "username": "admin",
            "password": pw,
            "is_superuser": True,
            "is_staff": True,
            "is_active": True
        }
    }
]

with open('radio/fixtures/default_admin.json', 'w') as f:
    json.dump(data, f, indent=4)

from radio.settings import BASE_URL

msg = """
############################################################

Default administrator account added as follows:

user: admin
password: {1}

Please access following url and change admin password:

{0}/admin/password_change/

Then access following url and add other users:

{0}/admin/auth/user/add/

############################################################
""".format(BASE_URL, raw_pw)

print(msg)

