from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import logging
import os
import requests

# Configuración de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configuración del cliente OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Configuración de Pipedrive
PIPEDRIVE_API_KEY = '8f2492eead4201ac69582ee4f3dfefd13d818b79'  # API token de Pipedrive
COMPANY_DOMAIN = 'companiademuestra'  # Dominio de tu cuenta de Pipedrive

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
        logger.debug(f"Asistente (on_text_created): {text.value}")
        self.assistant_message = text.value

    @override
    def on_text_delta(self, delta, snapshot):
        logger.debug(f"Delta (on_text_delta): {delta.value}")
        if not self.assistant_message.endswith(delta.value):
            self.assistant_message += delta.value

# Función para crear un lead en Pipedrive
def create_pipedrive_lead(name, organization=None, value=None):
    try:
        if not name:
            logger.error("El nombre del lead es obligatorio.")
            return "Error: El nombre del lead es obligatorio."
        
        lead_url = f"https://{COMPANY_DOMAIN}.pipedrive.com/v1/leads?api_token={PIPEDRIVE_API_KEY}"
        lead_data = {
            "title": name,
            "organization_name": organization,
            "value": value,
        }
        response = requests.post(lead_url, json=lead_data)
        
        if response.status_code == 201:
            logger.info(f"Lead creado exitosamente: {response.json()}")
            return "Lead creado exitosamente en Pipedrive."
        else:
            logger.error(f"Error al crear el lead: {response.text}")
            return f"Error al crear el lead: {response.text}"
    except Exception as e:
        logger.error(f"Error al interactuar con Pipedrive: {str(e)}")
        return f"Error al interactuar con Pipedrive: {str(e)}"

# Lógica principal del asistente
def handle_assistant_response(user_message, user_id):
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

        if "crear lead" in user_message.lower():
            name = extract_field(user_message, "nombre")
            organization = extract_field(user_message, "organización")
            value = extract_field(user_message, "valor")
            
            if value:
                try:
                    value = float(value)
                except ValueError:
                    logger.warning(f"Valor no válido: {value}. Se ignorará.")
                    value = None

            pipedrive_response = create_pipedrive_lead(name, organization, value)
            assistant_message += f"\n\n{pipedrive_response}"

        return assistant_message, None

    except Exception as e:
        logger.error(f"Error al procesar el mensaje: {str(e)}")
        return None, f"Error al procesar el mensaje: {str(e)}"

def extract_field(message, field_name):
    """
    Extrae un campo específico basado en el formato esperado.
    :param message: str, el mensaje del usuario
    :param field_name: str, el nombre del campo a buscar
    :return: str | None, el valor extraído o None si no se encuentra
    """
    try:
        field_lower = field_name.lower() + ":"
        if field_lower in message.lower():
            start = message.lower().index(field_lower) + len(field_lower)
            value = message[start:].split("\n")[0].strip()
            logger.debug(f"Campo extraído '{field_name}': {value}")
            return value
    except Exception as e:
        logger.warning(f"Error al extraer el campo '{field_name}': {str(e)}")
    return None
