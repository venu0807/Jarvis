import os
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def add_interview_to_calendar(company_name: str, date_time_str: str):
    """Adds the interview to Google Calendar."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("❌ credentials.json missing! Please download from Google Cloud Console.")
                return
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('calendar', 'v3', credentials=creds)
        
        event = {
            'summary': f'Interview: {company_name}',
            'description': f'Automated interview event for {company_name}.',
            'start': {
                'dateTime': date_time_str,
                'timeZone': 'Asia/Kolkata',
            },
            'end': {
                'dateTime': (datetime.datetime.fromisoformat(date_time_str) + datetime.timedelta(hours=1)).isoformat(),
                'timeZone': 'Asia/Kolkata',
            },
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        print(f"  ✅ Calendar Event created: {event.get('htmlLink')}")
        
    except Exception as error:
        print(f"❌ Calendar API error: {error}")

if __name__ == "__main__":
    # Test
    print("Calendar Integration initialized.")
