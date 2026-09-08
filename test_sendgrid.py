"""QuickHire SendGrid connection test.

Run this file from the QuickHire-main folder:
    .\\venv\\Scripts\\python.exe test_sendgrid.py

It never prints the SendGrid API key.
"""

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv

# Always load the .env file beside this script.
env_path = Path(__file__).with_name('.env')
load_dotenv(env_path, override=True)

api_key = os.getenv('SENDGRID_API_KEY', '').strip()
from_email = os.getenv('SENDGRID_FROM_EMAIL', '').strip()
from_name = os.getenv('SENDGRID_FROM_NAME', 'QuickHire').strip() or 'QuickHire'

print('QuickHire SendGrid test')
print('-----------------------')
print('Using .env:', env_path)
print('Found .env:', env_path.exists())
print('API key found:', bool(api_key))
print('API key looks valid:', api_key.startswith('SG.'))
print('Sender email:', from_email or '[missing]')
print('Sender name:', from_name)

if not api_key:
    raise SystemExit('\nERROR: SENDGRID_API_KEY is missing from .env')
if not api_key.startswith('SG.'):
    raise SystemExit('\nERROR: SENDGRID_API_KEY does not look like a SendGrid API key. It should start with SG.')
if not from_email or '@' not in from_email:
    raise SystemExit('\nERROR: SENDGRID_FROM_EMAIL is missing or invalid in .env')

# Send a harmless API request that checks whether the API key is accepted.
# This endpoint does not send an email.
request = Request(
    'https://api.sendgrid.com/v3/scopes',
    headers={'Authorization': f'Bearer {api_key}'},
    method='GET',
)

try:
    with urlopen(request, timeout=15) as response:
        body = response.read().decode('utf-8', errors='replace')
        print('\nAPI key test status:', response.getcode())
        try:
            data = json.loads(body)
            scopes = data.get('scopes', [])
        except Exception:
            scopes = []

        has_mail_send = 'mail.send' in scopes
        print('Mail Send permission:', has_mail_send)
        if not has_mail_send:
            print('ERROR: The API key does not have Mail Send permission.')
        else:
            print('SUCCESS: API key is valid and has Mail Send permission.')

except HTTPError as error:
    details = error.read().decode('utf-8', errors='replace')
    print('\nAPI key test failed.')
    print('HTTP status:', error.code)
    print('SendGrid response:', details)
    if error.code == 401:
        print('FIX: Create/copy a valid SendGrid API key and place the full SG... value in .env.')
    elif error.code == 403:
        print('FIX: Check API key permissions/account restrictions in SendGrid.')
    raise SystemExit(1)
except URLError as error:
    print('\nNETWORK ERROR:', error.reason)
    raise SystemExit(1)

print('\nIf the app still cannot send after this test succeeds, the next thing to check is Single Sender Verification.')
