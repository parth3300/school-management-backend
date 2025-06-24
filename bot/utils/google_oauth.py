import os
import datetime
from datetime import datetime as dt, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from bot.utils.token_generate import refresh_and_store_tokens
# You can use .env or Django settings to keep secrets
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN")
GOOGLE_ACCESS_TOKEN = os.getenv("GOOGLE_ACCESS_TOKEN")  # initial token

def create_google_meet_event(title, description, start_time, end_time, attendees):
    creds = Credentials(
        token=GOOGLE_ACCESS_TOKEN,
        refresh_token=GOOGLE_REFRESH_TOKEN,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET
    )

    print("Token expires at:", creds.expiry)

    # if creds.expired and creds.refresh_token:
    creds = refresh_and_store_tokens()
    print('creds----->',creds)
    service = build("calendar", "v3", credentials=creds)

    event = {
        "summary": title,
        "description": description,
        "start": {
            "dateTime": start_time,
            "timeZone": "UTC"
        },
        "end": {
            "dateTime": end_time,
            "timeZone": "UTC"
        },
        "attendees": attendees,  
        "conferenceData": {
            "createRequest": {
                "requestId": f"meet-{int(dt.utcnow().timestamp())}",
                "conferenceSolutionKey": {
                    "type": "hangoutsMeet"
                }
            }
        }
    }
    print("event",event)
    created_event = service.events().insert(
        calendarId='primary',
        body=event,
        conferenceDataVersion=1
    ).execute()

    return created_event.get("hangoutLink")
