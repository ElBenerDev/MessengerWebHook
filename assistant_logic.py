from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import os
import logging
from google_calendar_utils import create_event  # Asegúrate de que esta función sea importada correctamente
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
        logger.debug(f"Asistente: {text.value}")
        self.assistant_message += text.value

    @override
    def on_text_delta(self, delta, snapshot):
        logger.debug(f"Delta: {delta.value}")
        self.assistant_message += delta.value

def parse_event_details(assistant_message):
    """
    Extrae los detalles del evento del mensaje del asistente.
    Retorna un diccionario con los datos del evento o None si falta información clave.
    """
    try:
        # Aquí puedes ajustar la lógica de extracción según el formato de los mensajes generados
        lines = assistant_message.split("\n")
        title = next(line.split(":")[1].strip() for line in lines if "Título" in line)
        start = next(line.split(":")[1].strip() for line in lines if "Fecha y hora de inicio" in line)
        end = next(line.split(":")[1].strip() for line in lines if "Fecha y hora de finalización" in line)

        # Convertir las fechas a objetos datetime
        start_datetime = datetime.strptime(start, "%d de %B de %Y a las %I:%M %p")
        end_datetime = datetime.strptime(end, "%d de %B de %Y a las %I:%M %p")

        return {
            "summary": title,
            "start_time": start_datetime,
            "end_time": end_datetime,
        }
    except Exception as e:
        logger.error(f"Error al extraer detalles del evento: {str(e)}")
        return None

def handle_assistant_response(user_message, user_id):
    """ Maneja la respuesta del asistente de OpenAI. """
    try:
        if user_id not in user_threads:
            thread = client.beta.threads.create()
            logger.info(f"Hilo creado para el usuario {user_id}: {thread.id}")
            user_threads[user_id] = thread.id

        client.beta.threads.messages.create(
            thread_id=user_threads[user_id],
            role="user",
            content=user_message
        )

        event_handler = EventHandler()
        with client.beta.threads.runs.stream(
            thread_id=user_threads[user_id],
            assistant_id=assistant_id,
            event_handler=event_handler,
        ) as stream:
            stream.until_done()

        assistant_message = event_handler.assistant_message.strip()
        logger.info(f"Mensaje generado por el asistente: {assistant_message}")

        # Intentar extraer detalles del evento
        event_details = parse_event_details(assistant_message)
        if event_details:
            # Crear el evento en Google Calendar
            created_event = create_event(
                start_time=event_details["start_time"],
                end_time=event_details["end_time"],
                summary=event_details["summary"]
            )
            logger.info(f"Evento creado: {created_event.get('htmlLink')}")
            assistant_message += f"\n\nEl evento ha sido creado con éxito: {created_event.get('htmlLink')}"
        else:
            logger.info("No se detectaron detalles de evento en el mensaje del asistente.")

        return assistant_message, None

    except Exception as e:
        logger.error(f"Error al generar respuesta: {str(e)}")
        return None, str(e)
