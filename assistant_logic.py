from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import os
import logging
from datetime import datetime
from googleapiclient.errors import HttpError
from google_calendar_utils import create_event  # Este es tu módulo para Google Calendar
import re

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configura tu cliente OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
assistant_id = os.getenv("ASSISTANT_ID", "asst_d2QBbmcrr6vdZgxusPdqNOtY")

# Diccionario para almacenar el thread_id de cada usuario
user_threads = {}

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


def extract_event_details(message):
    """Extrae detalles de un evento desde un mensaje del usuario."""
    try:
        # Patrón para fechas y horas
        date_pattern = r"\b(\d{4}-\d{2}-\d{2})\b"
        time_pattern = r"\b(\d{2}:\d{2})\b"
        summary_pattern = r"título[:]? (.+?)(,|$)"

        dates = re.findall(date_pattern, message)
        times = re.findall(time_pattern, message)
        summary_match = re.search(summary_pattern, message, re.IGNORECASE)

        if not dates or len(times) < 2 or not summary_match:
            raise ValueError("Faltan datos clave para el evento.")

        start_date = dates[0]
        start_time = times[0]
        end_time = times[1]
        summary = summary_match.group(1).strip()

        start_datetime = datetime.fromisoformat(f"{start_date}T{start_time}")
        end_datetime = datetime.fromisoformat(f"{start_date}T{end_time}")

        return start_datetime, end_datetime, summary
    except Exception as e:
        logger.error(f"Error al extraer detalles del evento: {e}")
        return None, None, None


def handle_assistant_response(user_message, user_id):
    """Maneja la interacción del usuario con el asistente y Google Calendar."""
    try:
        # Crear o usar el hilo del usuario
        if user_id not in user_threads:
            thread = client.beta.threads.create()
            logger.info(f"Hilo creado para el usuario {user_id}: {thread.id}")
            user_threads[user_id] = thread.id

        client.beta.threads.messages.create(
            thread_id=user_threads[user_id],
            role="user",
            content=user_message
        )

        # Manejar respuesta del asistente
        event_handler = EventHandler()
        with client.beta.threads.runs.stream(
            thread_id=user_threads[user_id],
            assistant_id=assistant_id,
            event_handler=event_handler,
        ) as stream:
            stream.until_done()

        assistant_message = event_handler.assistant_message.strip()
        logger.info(f"Respuesta del asistente: {assistant_message}")

        # Intentar extraer detalles del evento
        start_time, end_time, summary = extract_event_details(user_message)

        if start_time and end_time and summary:
            try:
                event = create_event(start_time, end_time, summary)
                return f"Evento creado exitosamente: {event.get('htmlLink')}", None
            except HttpError as e:
                logger.error(f"Error al crear el evento en Google Calendar: {e}")
                return None, f"Error al crear el evento en Google Calendar: {e}"

        return assistant_message, None

    except Exception as e:
        logger.error(f"Error general en el manejo de la respuesta: {e}")
        return None, str(e)
