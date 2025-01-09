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

def create_event(start_time, end_time, summary, description=None, attendees=None, reminders=None):
    """Crea un evento en Google Calendar."""
    try:
        service = build_service()
        event = {
            'summary': summary,
            'description': description,
            'start': {'dateTime': start_time.isoformat(), 'timeZone': 'America/Argentina/Buenos_Aires'},
            'end': {'dateTime': end_time.isoformat(), 'timeZone': 'America/Argentina/Buenos_Aires'},
            'attendees': attendees or [],
            'reminders': {'useDefault': False, 'overrides': reminders or []}
        }
        event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        logging.info(f"Evento creado: {event.get('htmlLink')}")
        return event
    except Exception as e:
        logging.error(f"Error al crear el evento: {e}")
        raise

def delete_event(event_summary):
    """Elimina un evento basado en su resumen."""
    try:
        service = build_service()
        events_result = service.events().list(
            calendarId=CALENDAR_ID, timeMin=datetime.utcnow().isoformat() + 'Z', singleEvents=True, orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        for event in events:
            if event_summary.lower() in event['summary'].lower():
                service.events().delete(calendarId=CALENDAR_ID, eventId=event['id']).execute()
                return f"El evento '{event['summary']}' ha sido cancelado con éxito."
        return "No se encontró el evento."
    except Exception as e:
        logging.error(f"Error al eliminar evento: {e}")
        raise

def list_events():
    """Lista los eventos en el calendario."""
    try:
        service = build_service()
        events_result = service.events().list(
            calendarId=CALENDAR_ID, timeMin=datetime.utcnow().isoformat() + 'Z', singleEvents=True, orderBy='startTime'
        ).execute()

        return events_result.get('items', [])
    except Exception as e:
        logging.error(f"Error al listar eventos: {e}")
        raise
