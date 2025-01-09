from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import logging
import os

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Parámetros de Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', '/etc/secrets/GOOGLE_SERVICE_ACCOUNT_FILE.json')
CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')

# Validar si la variable de entorno CALENDAR_ID está presente
if not CALENDAR_ID:
    logger.error("No se ha definido la variable de entorno 'GOOGLE_CALENDAR_ID'.")
    raise EnvironmentError("La variable de entorno 'GOOGLE_CALENDAR_ID' no está configurada.")

def build_service():
    """Crea y devuelve un servicio de Google Calendar."""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        service = build('calendar', 'v3', credentials=credentials)
        logger.info("Servicio de Google Calendar creado correctamente.")
        return service
    except Exception as e:
        logger.error(f"Error al crear el servicio de Google Calendar: {e}")
        raise

def validate_event_data(summary, start_time, end_time):
    """Valida los datos del evento antes de la creación."""
    if not summary:
        raise ValueError("El título del evento es obligatorio.")
    if not start_time or not end_time:
        raise ValueError("Las fechas y horas de inicio y fin son obligatorias.")
    if start_time >= end_time:
        raise ValueError("La hora de inicio debe ser anterior a la hora de fin.")

def create_event(start_time, end_time, summary, description=None, attendees=None, reminders=None):
    """Crea un evento en Google Calendar."""
    try:
        # Validar los datos del evento
        validate_event_data(summary, start_time, end_time)
        
        # Crear el evento en Google Calendar
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
            'attendees': attendees or [],
            'reminders': {
                'useDefault': False,
                'overrides': reminders or [],
            }
        }

        # Insertar el evento en el calendario
        event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        logger.info(f'Evento creado: {event.get("htmlLink")}')
        return event, None
    except ValueError as ve:
        logger.error(f"Validación fallida: {ve}")
        return None, f"Error en los datos del evento: {ve}"
    except Exception as e:
        logger.error(f"Error al crear el evento: {e}")
        return None, f"Hubo un error al crear el evento: {e}"

def delete_event(event_summary, min_time=None, max_time=None):
    """Elimina un evento basado en su resumen y rango de tiempo."""
    try:
        service = build_service()
        now = datetime.utcnow().isoformat() + 'Z'
        time_min = min_time or now
        time_max = max_time or (datetime.utcnow() + timedelta(days=30)).isoformat() + 'Z'

        # Buscar los eventos dentro del rango de tiempo
        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        logger.info(f"{len(events)} eventos encontrados para analizar.")

        for event in events:
            logger.debug(f"Analizando evento: {event['summary']} con ID {event['id']}")
            if event_summary.lower() in event['summary'].lower():
                # Eliminar el evento
                service.events().delete(calendarId=CALENDAR_ID, eventId=event['id']).execute()
                logger.info(f"Evento eliminado: {event['summary']}")
                return f"El evento '{event['summary']}' ha sido cancelado con éxito."

        logger.warning(f"No se encontró el evento con el resumen: {event_summary}")
        return f"No se encontró el evento '{event_summary}' en el rango de tiempo especificado."

    except Exception as e:
        logger.error(f"Error al eliminar el evento: {e}")
        return f"Hubo un error al intentar cancelar el evento: {e}"

def list_events(time_min=None, time_max=None):
    """Lista los eventos en el calendario entre un rango de tiempo."""
    try:
        service = build_service()
        time_min = time_min or datetime.utcnow().isoformat() + 'Z'
        time_max = time_max or (datetime.utcnow() + timedelta(days=30)).isoformat() + 'Z'

        # Obtener los eventos dentro del rango de tiempo
        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        logger.info(f"Se encontraron {len(events)} eventos.")
        return events, None

    except Exception as e:
        logger.error(f"Error al listar eventos: {e}")
        return [], f"Hubo un error al listar los eventos: {e}"

