from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import os
import logging
from google_calendar_utils import create_event  # Asegúrate de que esta función esté importada correctamente
from datetime import datetime, timedelta
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
        # Al recibir texto del asistente, lo acumulamos y lo mostramos
        logger.debug(f"Asistente: {text.value}")
        self.assistant_message += text.value

    @override
    def on_text_delta(self, delta, snapshot):
        # Maneja las actualizaciones parciales del mensaje
        logger.debug(f"Delta: {delta.value}")
        self.assistant_message += delta.value

def handle_assistant_response(user_message, user_id):
    """ Maneja la respuesta del asistente de OpenAI. """
    try:
        # Verificar si ya existe un thread_id para este usuario
        if user_id not in user_threads:
            thread = client.beta.threads.create()
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

        # Buscar fecha y hora en el mensaje del usuario
        datetime_pattern = r'(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})'
        match = re.search(datetime_pattern, user_message)
        if match:
            date_str, time_str = match.groups()
            start_time = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M')
            end_time = start_time + timedelta(hours=1)  # Duración predeterminada de 1 hora
            summary = "Evento desde Asistente"

            # Crear evento en Google Calendar
            try:
                event = create_event(start_time, end_time, summary)
                return f"Evento creado con éxito: {event.get('htmlLink')}", None
            except Exception as e:
                return None, f"Error al crear el evento: {e}"

        return assistant_message, None

    except Exception as e:
        return None, str(e)