from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime
import logging
import os

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Parámetros de Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = '/etc/secrets/GOOGLE_SERVICE_ACCOUNT_FILE.json'
CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')

def build_service():
    """Crea y devuelve un servicio de Google Calendar."""
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('calendar', 'v3', credentials=credentials)

def create_event(start_time, end_time, summary, description=None):
    try:
        service = build_service()
        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'America/Argentina/Buenos_Aires',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'America/Argentina/Buenos_Aires',
            },
        }
        event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        logger.info(f'Evento creado: {event.get("htmlLink")}')
        return event
    except Exception as e:
        logger.error(f"Error al crear el evento: {e}")
        return None

def delete_event(event_summary):
    try:
        service = build_service()
        now = datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(calendarId=CALENDAR_ID, timeMin=now, singleEvents=True, orderBy='startTime').execute()
        events = events_result.get('items', [])

        logger.info(f"{len(events)} eventos encontrados para analizar.")

        for event in events:
            logger.debug(f"Analizando evento: {event['summary']} con ID {event['id']}")
            if event_summary.lower() in event['summary'].lower():
                service.events().delete(calendarId=CALENDAR_ID, eventId=event['id']).execute()
                logger.info(f"Evento eliminado: {event['summary']}")
                return f"El evento '{event['summary']}' ha sido cancelado con éxito."

        logger.warning(f"No se encontró el evento con el resumen: {event_summary}")
        return f"No se encontró el evento '{event_summary}'."
    except Exception as e:
        logger.error(f"Error al eliminar el evento: {e}")
        return f"Hubo un error al intentar cancelar el evento: {e}"