from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import os
import logging
from google_calendar_utils import create_event  # Asegúrate de que esta función esté importada correctamente
from datetime import datetime
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configura tu cliente con la API key desde el entorno
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ID del asistente
assistant_id = os.getenv("ASSISTANT_ID", "asst_d2QBbmcrr6vdZgxusPdqNOtY")

# Diccionario para almacenar el thread_id de cada usuario
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

def build_service():
    """Crea y devuelve un servicio de Google Calendar."""
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', '/etc/secrets/GOOGLE_SERVICE_ACCOUNT_FILE.json')
    CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')

    # Validar si la variable de entorno CALENDAR_ID está presente
    if not CALENDAR_ID:
        raise EnvironmentError("La variable de entorno 'GOOGLE_CALENDAR_ID' no está configurada.")

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
        event = service.events().insert(calendarId=os.getenv('GOOGLE_CALENDAR_ID'), body=event).execute()
        logging.info(f"Evento creado: {event.get('htmlLink')}")
        return event
    except Exception as e:
        logging.error(f"Error al crear el evento: {e}")
        raise

def handle_assistant_response(user_message, user_id):
    """ Maneja la respuesta del asistente de OpenAI. """
    try:
        # Verificar si ya existe un thread_id para este usuario
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

        return assistant_message

    except Exception as e:
        logger.error(f"Error al generar respuesta: {str(e)}")
        return None, str(e)

def handle_user_confirmation(message, user_id, event_details):
    """ Maneja la confirmación del usuario para crear el evento. """
    if message.strip().lower() == "sí":
        start_time, end_time, title = event_details
        if start_time and end_time and title:
            try:
                event = create_event(start_time, end_time, title)
                return f"Evento creado exitosamente: {event.get('htmlLink')}", None
            except Exception as e:
                logger.error(f"Error al crear el evento: {e}")
                return None, f"Error al crear el evento: {e}"
        else:
            return None, "No se pudieron extraer todos los detalles del evento."
    return None, "Confirmación no recibida. Por favor, confirma los detalles del evento."

def ask_for_event_details(user_id, step="title"):
    """Función que se encarga de preguntar al usuario por los detalles del evento paso a paso."""
    if step == "title":
        return "¿Cómo te gustaría llamar al evento?"
    elif step == "date":
        return "¿Qué día será el evento? (Por ejemplo, 11 de enero de 2025)"
    elif step == "start_time":
        return "¿A qué hora comienza el evento? (Por ejemplo, 10:00 AM)"
    elif step == "end_time":
        return "¿A qué hora termina el evento? (Por ejemplo, 11:00 AM)"
    return "Por favor, proporciona los detalles del evento."

def handle_conversation(user_message, user_id):
    """Controla la conversación completa con el asistente"""
    user_data = {}

    # Primera interacción, pregunta el título del evento
    if user_message.strip().lower() == "hola":
        response = ask_for_event_details(user_id, step="title")
        return response, user_data

    if "title" not in user_data:
        user_data["title"] = user_message
        response = ask_for_event_details(user_id, step="date")
        return response, user_data

    if "date" not in user_data:
        user_data["date"] = user_message
        response = ask_for_event_details(user_id, step="start_time")
        return response, user_data

    if "start_time" not in user_data:
        user_data["start_time"] = user_message
        response = ask_for_event_details(user_id, step="end_time")
        return response, user_data

    if "end_time" not in user_data:
        user_data["end_time"] = user_message
        # Confirmar los detalles
        response = f"Perfecto! He recogido todos los detalles:\n\n"\
                   f"Título: {user_data['title']}\n"\
                   f"Fecha: {user_data['date']}\n"\
                   f"Hora de inicio: {user_data['start_time']}\n"\
                   f"Hora de fin: {user_data['end_time']}\n\n"\
                   f"¿Es todo correcto? (Sí/No)"
        return response, user_data
    return "Algo salió mal. Vuelve a intentarlo.", user_data
