from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import os
import logging

# Parámetros de Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', '/etc/secrets/GOOGLE_SERVICE_ACCOUNT_FILE.json')
CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')

# Validar si la variable de entorno CALENDAR_ID está presente
if not CALENDAR_ID:
    raise EnvironmentError("La variable de entorno 'GOOGLE_CALENDAR_ID' no está configurada.")

def build_service():
    """Crea y devuelve un servicio de Google Calendar."""
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build('calendar', 'v3', credentials=credentials)

def create_event(start_time, end_time, summary):
    """Crea un evento en Google Calendar con los parámetros básicos."""
    try:
        service = build_service()
        event = {
            'summary': summary,
            'start': {'dateTime': start_time.isoformat(), 'timeZone': 'America/Argentina/Buenos_Aires'},
            'end': {'dateTime': end_time.isoformat(), 'timeZone': 'America/Argentina/Buenos_Aires'},
        }
        event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        logging.info(f"Evento creado: {event.get('htmlLink')}")
        return event
    except Exception as e:
        logging.error(f"Error al crear el evento: {e}")
        raise
