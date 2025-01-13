import requests
from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import logging
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
        logger.debug(f"Asistente (on_text_created): {text.value}")
        self.assistant_message = text.value

    @override
    def on_text_delta(self, delta, snapshot):
        logger.debug(f"Delta (on_text_delta): {delta.value}")
        if not self.assistant_message.endswith(delta.value):
            self.assistant_message += delta.value

# Función de creación de organización, lead y actividad de Pipedrive
def create_organization(name):
    PIPEDRIVE_API_KEY = '8f2492eead4201ac69582ee4f3dfefd13d818b79'
    COMPANY_DOMAIN = 'companiademuestra'
    organization_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/organizations?api_token={PIPEDRIVE_API_KEY}'
    organization_data = {'name': name}
    response = requests.post(organization_url, json=organization_data)
    if response.status_code == 201:
        organization = response.json()
        return organization['data']['id']
    else:
        logger.error(f"Error al crear la organización: {response.status_code}")
        return None

def create_lead(title, organization_id):
    PIPEDRIVE_API_KEY = '8f2492eead4201ac69582ee4f3dfefd13d818b79'
    COMPANY_DOMAIN = 'companiademuestra'
    lead_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/leads?api_token={PIPEDRIVE_API_KEY}'
    lead_data = {'title': title, 'organization_id': organization_id}
    response = requests.post(lead_url, json=lead_data)
    if response.status_code == 201:
        return response.json()['data']['id']
    else:
        logger.error(f"Error al crear el lead: {response.status_code}")
        return None

def create_activity(subject, due_date, due_time, lead_id):
    PIPEDRIVE_API_KEY = '8f2492eead4201ac69582ee4f3dfefd13d818b79'
    COMPANY_DOMAIN = 'companiademuestra'
    activity_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/activities?api_token={PIPEDRIVE_API_KEY}'
    activity_data = {
        'subject': subject,
        'type': 'meeting',
        'due_date': due_date,
        'due_time': due_time,
        'duration': '01:00',
        'lead_id': lead_id
    }
    response = requests.post(activity_url, json=activity_data)
    if response.status_code == 201:
        logger.info("Actividad creada exitosamente!")
    else:
        logger.error(f"Error al crear la actividad: {response.status_code}")

# Lógica principal del asistente
def handle_assistant_response(user_message, user_id):
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

        # Una vez obtenida la respuesta del asistente, ejecutamos el flujo de Pipedrive
        organization_name = "Nueva Organización de Ejemplo"
        organization_id = create_organization(organization_name)

        if organization_id:
            lead_title = "Manuel"
            lead_id = create_lead(lead_title, organization_id)

            if lead_id:
                activity_subject = "Reunión inicial con cliente"
                activity_due_date = "2025-01-13"
                activity_due_time = "17:00"
                create_activity(activity_subject, activity_due_date, activity_due_time, lead_id)

        return assistant_message, None

    except Exception as e:
        logger.error(f"Error al procesar el mensaje: {str(e)}")
        return None, f"Error al procesar el mensaje: {str(e)}"
