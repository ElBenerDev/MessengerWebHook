from openai import OpenAI
import logging
import os

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configura tu cliente con la API key desde el entorno
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ID del asistente
assistant_id = os.getenv("ASSISTANT_ID", "asst_d2QBbmcrr6vdZgxusPdqNOtY")

# Diccionario para almacenar el thread_id de cada usuario
user_threads = {}

class EventHandler:
    def __init__(self):
        self.assistant_message = ""
        self.message_complete = False

    def on_text_created(self, text):
        if not self.message_complete and text.value not in self.assistant_message:
            self.assistant_message += text.value

    def on_text_delta(self, delta, snapshot):
        if not self.message_complete and delta.value not in self.assistant_message:
            self.assistant_message += delta.value

    def finalize_message(self):
        if not self.message_complete:
            self.message_complete = True
        return self.assistant_message.strip()

def handle_assistant_response(user_message, user_id):
    if not user_message or not user_id:
        logger.error("No se proporcionó un mensaje o ID de usuario válido.")
        return None, "No se proporcionó un mensaje o ID de usuario válido."

    logger.info(f"Mensaje recibido del usuario {user_id}: {user_message}")

    try:
        if user_id not in user_threads:
            thread = client.beta.threads.create()
            user_threads[user_id] = thread.id
        thread_id = user_threads[user_id]

        event_handler = EventHandler()
        with client.beta.threads.runs.stream(
            thread_id=thread_id,
            assistant_id=assistant_id,
            event_handler=event_handler,
        ) as stream:
            stream.until_done()

        assistant_message = event_handler.finalize_message()
        logger.info(f"Mensaje generado por el asistente: {assistant_message}")
        return assistant_message, None

    except Exception as e:
        logger.error(f"Error al generar respuesta: {e}")
        return None, f"Error al generar respuesta: {e}"