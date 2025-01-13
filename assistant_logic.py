from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import logging
import os
import requests

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración del cliente OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Configuración de Pipedrive
PIPEDRIVE_API_KEY = os.getenv("PIPEDRIVE_API_KEY")
COMPANY_DOMAIN = os.getenv("PIPEDRIVE_COMPANY_DOMAIN")

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
        # Capturamos la respuesta inicial completa
        self.assistant_message = text.value

    @override
    def on_text_delta(self, delta, snapshot):
        logger.debug(f"Delta (on_text_delta): {delta.value}")
        # Concatenamos solo los deltas adicionales si no hay repetición
        if not self.assistant_message.endswith(delta.value):
            self.assistant_message += delta.value

# Función para crear un lead en Pipedrive
def create_pipedrive_lead(name, organization=None, value=None):
    """
    Crea un lead en Pipedrive con los datos proporcionados.
    :param name: str, nombre del lead
    :param organization: str, nombre de la organización (opcional)
    :param value: float, valor del lead (opcional)
    :return: str | None, mensaje de éxito o error
    """
    try:
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

        # Lógica adicional: Crear leads en Pipedrive si el mensaje lo solicita
        if "crear lead" in user_message.lower():
            name = "Lead sin nombre"  # Valor predeterminado
            organization = None
            value = None

            # Analizar detalles adicionales desde el mensaje
            # (Puedes personalizar este análisis para extraer valores específicos)
            if "nombre:" in user_message.lower():
                name = user_message.split("nombre:")[1].split()[0]
            if "organización:" in user_message.lower():
                organization = user_message.split("organización:")[1].split()[0]
            if "valor:" in user_message.lower():
                value = float(user_message.split("valor:")[1].split()[0])

            pipedrive_response = create_pipedrive_lead(name, organization, value)
            assistant_message += f"\n\n{pipedrive_response}"

        return assistant_message, None

    except Exception as e:
        logger.error(f"Error al procesar el mensaje: {str(e)}")
        return None, f"Error al procesar el mensaje: {str(e)}"
