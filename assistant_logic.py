from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import os
import logging
from google_calendar_utils import create_event  # Asegúrate de que esta función esté importada correctamente
from datetime import datetime
import re

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

def parse_datetime_from_user_message(user_message):
    """ Extrae fecha, hora de inicio y hora de fin de un mensaje del usuario. """
    # Usar expresiones regulares para encontrar fechas y horas en el mensaje
    date_pattern = r"\b(\d{4}-\d{2}-\d{2})\b"  # Formato de fecha YYYY-MM-DD
    time_pattern = r"\b(\d{2}:\d{2})\b"        # Formato de hora HH:MM

    dates = re.findall(date_pattern, user_message)
    times = re.findall(time_pattern, user_message)

    if dates and len(times) >= 2:  # Necesitamos al menos una fecha y dos horas
        start_date = dates[0]
        start_time = times[0]
        end_time = times[1]
        start_datetime = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
        end_datetime = datetime.strptime(f"{start_date} {end_time}", "%Y-%m-%d %H:%M")
        return start_datetime, end_datetime

    return None, None

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

        # Intentar extraer fecha y hora del mensaje del usuario
        start_time, end_time = parse_datetime_from_user_message(user_message)
        if not start_time or not end_time:
            return (
                "No pude entender las fechas y horas del evento. Por favor, proporciona el formato YYYY-MM-DD HH:MM.",
                None,
            )

        # Crear el evento con la información proporcionada
        summary = "Evento del asistente"
        try:
            event = create_event(start_time, end_time, summary)
            logger.info(f"Evento creado con éxito: {event.get('htmlLink')}")
            return f"Evento creado con éxito: {event.get('htmlLink')}", None
        except Exception as e:
            logger.error(f"Error al crear el evento: {e}")
            return None, str(e)

    except Exception as e:
        logger.error(f"Error al generar respuesta: {str(e)}")
        return None, str(e)