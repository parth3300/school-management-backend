import os
import json
from datetime import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from dotenv import load_dotenv

# Load existing environment variables
load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/calendar.events']

CLIENT_CONFIG = {
    "web": {
        "client_id": os.environ.get('GOOGLE_CLIENT_ID'),
        "project_id": os.environ.get('PROJECT_ID'),
        "auth_uri": os.environ.get('AUTH_URL'),
        "token_uri": os.environ.get('TOKEN_URL'),
        "auth_provider_x509_cert_url": os.environ.get('AUTH_PROVIDER_X509_CERT_URL'),
        "client_secret": os.environ.get('GOOGLE_CLIENT_SECRET'),
        "redirect_uris": os.environ.get('REFIRECT_URLS'),
        "javascript_origins": os.environ.get('JAVASCRIPT_ORIGINS')
    }
}


ENV_PATH = '.env'
TOKEN_JSON = 'token.json'

def save_to_env(access_token: str, refresh_token: str = None):
    env = {}
    if os.path.exists(ENV_PATH):
        for line in open(ENV_PATH):
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1); env[k] = v
    env['GOOGLE_ACCESS_TOKEN'] = access_token
    if refresh_token:
        env['GOOGLE_REFRESH_TOKEN'] = refresh_token
    with open(ENV_PATH, 'w') as f:
        for k, v in env.items():
            f.write(f'{k}={v}\n')

def load_credentials() -> Credentials:
    creds = None
    # 1) Try to load from token.json
    try:
        if os.path.exists(TOKEN_JSON):
            data = json.load(open(TOKEN_JSON))
            creds = Credentials.from_authorized_user_info(data, SCOPES)
            print("Loaded credentials from token.json")


        # 2) If no creds or invalid, try environment

        elif (not creds or not creds.valid) and os.getenv('GOOGLE_ACCESS_TOKEN') and os.getenv('GOOGLE_REFRESH_TOKEN'):
            creds = Credentials(
                token=os.getenv('GOOGLE_ACCESS_TOKEN'),
                refresh_token=os.getenv('GOOGLE_REFRESH_TOKEN'),
                token_uri=CLIENT_CONFIG['web']['token_uri'],
                client_id=CLIENT_CONFIG['web']['client_id'],
                client_secret=CLIENT_CONFIG['web']['client_secret'],
                scopes=SCOPES
            )
            print("Loaded credentials from environment variables")
    except Exception as e:
        print(f"Error loading credentials from env: {e}")
        creds = None

    return creds

def refresh_and_store_tokens() -> Credentials:
    """
    Ensures we have valid credentials:
    - Refreshes if expired & refresh_token present
    - Otherwise runs full OAuth flow
    Saves tokens back to token.json and .env
    """
    creds = load_credentials()

    if creds and creds.valid:
        print("✅ Loaded valid credentials.")
    elif creds and creds.expired and creds.refresh_token:
        print("🔁 Refreshing expired token...")
        creds.refresh(Request())
    else:
        print("🆕 No valid credentials, starting OAuth flow...")
        flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, SCOPES)
        creds = flow.run_local_server(port=8000)

    save_to_env(creds.token, creds.refresh_token)
    # Save updated credentials
    with open(TOKEN_JSON, 'w') as f:
        f.write(creds.to_json())
    save_to_env(creds.token, creds.refresh_token)

    print(f"🔑 Access token: {creds.token}")
    print(f"🔄 Refresh token: {creds.refresh_token}")
    print(f"⏰ Expires at: {creds.expiry.isoformat() if creds.expiry else 'unknown'}")

    return creds
