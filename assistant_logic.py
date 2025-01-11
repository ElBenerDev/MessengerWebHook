from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import logging
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración del cliente OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ID del asistente
assistant_id = os.getenv("ASSISTANT_ID", "asst_d2QBbmcrr6vdZgxusPdqNOtY")

# Diccionario para almacenar los hilos por usuario
user_threads = {}

# Crear un manejador de eventos para manejar el stream de respuestas del asistente
class EventHandler(AssistantEventHandler):
    def __init__(self):
        super().__init__()
        self.assistant_message = ""

    @override
    def on_text_created(self, text) -> None:
        logger.debug(f"Asistente: {text.value}")
        self.assistant_message += text.value

    @override
    def on_text_delta(self, delta, snapshot):
        logger.debug(f"Delta: {delta.value}")
        self.assistant_message += delta.value

# Función para crear un servicio de Google Calendar
def build_service():
    """Crea y devuelve un servicio de Google Calendar."""
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'credentials.json')
    CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')

    if not CALENDAR_ID:
        raise EnvironmentError("La variable de entorno 'GOOGLE_CALENDAR_ID' no está configurada.")

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build('calendar', 'v3', credentials=credentials)

# Función para crear eventos en Google Calendar
def create_event(start_time, end_time, summary):
    """Crea un evento en Google Calendar con los parámetros básicos."""
    try:
        service = build_service()
        event = {
            'summary': summary,
            'start': {'dateTime': start_time.isoformat(), 'timeZone': 'America/Mexico_City'},
            'end': {'dateTime': end_time.isoformat(), 'timeZone': 'America/Mexico_City'},
        }
        event = service.events().insert(calendarId=os.getenv('GOOGLE_CALENDAR_ID'), body=event).execute()
        logger.info(f"Evento creado: {event.get('htmlLink')}")
        return event
    except Exception as e:
        logger.error(f"Error al crear el evento: {e}")
        raise

# Lógica principal del asistente
def handle_assistant_response(user_message, user_id):
    """
    Procesa el mensaje del usuario y devuelve una respuesta generada por el asistente.
    :param user_message: str, mensaje del usuario
    :param user_id: str, identificador único del usuario
    :return: (str, str | None) respuesta generada, error (si ocurre)
    """
    try:
        # Verificar si ya existe un hilo para este usuario
        if user_id not in user_threads:
            thread = client.beta.threads.create()
            logger.info(f"Hilo creado para el usuario {user_id}: {thread.id}")
            user_threads[user_id] = thread.id

        # Enviar el mensaje del usuario al hilo existente
        client.beta.threads.messages.create(
            thread_id=user_threads[user_id],
            role="user",
            content=user_message
        )

        # Crear y manejar la respuesta del asistente
        event_handler = EventHandler()
        with client.beta.threads.runs.stream(
            thread_id=user_threads[user_id],
            assistant_id=assistant_id,
            event_handler=event_handler,
        ) as stream:
            stream.until_done()

        assistant_message = event_handler.assistant_message.strip()
        logger.info(f"Mensaje generado por el asistente: {assistant_message}")

        # Verificar si el mensaje contiene comandos para crear un evento
        if "crear evento" in user_message.lower():
            start_time = datetime.now()
            end_time = start_time.replace(hour=start_time.hour + 1)
            summary = "Evento de prueba"
            event = create_event(start_time, end_time, summary)
            return f"Evento creado con éxito: {event.get('htmlLink')}", None

        return assistant_message, None

    except Exception as e:
        logger.error(f"Error al procesar el mensaje: {str(e)}")
        return None, f"Error al procesar el mensaje: {str(e)}"
