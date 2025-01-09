from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import os
import logging
from google_calendar_utils import create_event  # Asegúrate de que esta función esté importada correctamente
from datetime import datetime

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
            # Crear un nuevo hilo de conversación si no existe
            thread = client.beta.threads.create()
            logger.info(f"Hilo creado para el usuario {user_id}: {thread.id}")
            user_threads[user_id] = thread.id
        else:
            thread_id = user_threads[user_id]

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

        # Obtener el mensaje generado por el asistente
        assistant_message = event_handler.assistant_message.strip()
        logger.info(f"Mensaje generado por el asistente: {assistant_message}")

        # Si el mensaje es "Correcto", creamos el evento en Google Calendar
        if "correcto" in assistant_message.lower():
            logger.info("Confirmación de creación de evento recibida. Creando evento en Google Calendar...")

            # Datos del evento para crear
            start_time = datetime(2025, 1, 10, 14, 0)  # Fechas del ejemplo
            end_time = datetime(2025, 1, 10, 15, 0)
            summary = "Proyecto"
            description = "Discutir sobre el proyecto"
            attendees = [{"email": "bernardoraos90@gmail.com"}]
            reminders = [{"method": "email", "minutes": 10}]  # Ejemplo de recordatorio

            try:
                event = create_event(start_time, end_time, summary, description, attendees, reminders)
                logger.info(f"Evento creado con éxito: {event.get('htmlLink')}")
                return f"Evento creado con éxito: {event.get('htmlLink')}", None
            except Exception as e:
                logger.error(f"Error al crear el evento: {e}")
                return None, str(e)

        return assistant_message, None

    except Exception as e:
        logger.error(f"Error al generar respuesta: {str(e)}")
        return None, str(e)
