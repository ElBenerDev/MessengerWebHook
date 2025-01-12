from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import logging
import os
import requests
import re

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración del cliente OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ID del asistente
assistant_id = os.getenv("ASSISTANT_ID", "asst_d2QBbmcrr6vdZgxusPdqNOtY")

# Datos de autenticación Pipedrive
PIPEDRIVE_API_KEY = os.getenv("PIPEDRIVE_API_KEY", "8f2492eead4201ac69582ee4f3dfefd13d818b79")
COMPANY_DOMAIN = os.getenv("PIPEDRIVE_COMPANY_DOMAIN", "companiademuestra")

# Diccionario para almacenar los hilos y contexto por usuario
user_threads = {}
user_context = {}

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

# Crear una organización en Pipedrive
def create_organization(name):
    organization_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/organizations?api_token={PIPEDRIVE_API_KEY}'
    organization_data = {'name': name}
    response = requests.post(organization_url, json=organization_data)
    if response.status_code == 201:
        organization = response.json()
        return organization['data']['id']
    else:
        logger.error(f"Error al crear la organización: {response.text}")
        return None

# Crear un lead en Pipedrive
def create_lead(title, organization_id):
    lead_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/leads?api_token={PIPEDRIVE_API_KEY}'
    lead_data = {'title': title, 'organization_id': organization_id}
    response = requests.post(lead_url, json=lead_data)
    if response.status_code == 201:
        lead = response.json()
        return lead['data']['id']
    else:
        logger.error(f"Error al crear el lead: {response.text}")
        return None

# Crear una actividad en Pipedrive
def create_activity(subject, due_date, due_time, lead_id):
    activity_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/activities?api_token={PIPEDRIVE_API_KEY}'
    activity_data = {
        'subject': subject,
        'type': 'meeting',
        'due_date': due_date,
        'due_time': due_time,
        'duration': '01:00',
        'lead_id': lead_id,
    }
    response = requests.post(activity_url, json=activity_data)
    if response.status_code == 201:
        logger.info("Actividad creada exitosamente!")
    else:
        logger.error(f"Error al crear la actividad: {response.text}")

# Extraer datos clave del mensaje del usuario
def extract_user_data(message, context):
    # Patrones de extracción de datos
    email_pattern = r"[\w\.-]+@[\w\.-]+\.\w+"
    phone_pattern = r"\b\d{10}\b|\b\d{7}\b|\+?\d[\d\s-]{8,}\d"
    name_pattern = r"(?i)(mi nombre es|soy|me llamo)\s([\w\s]+)"
    service_pattern = r"(?i)(busco|necesito|quiero)\s([\w\s]+)"

    # Extraer datos según patrones
    email = re.search(email_pattern, message)
    phone = re.search(phone_pattern, message)
    name = re.search(name_pattern, message)
    service = re.search(service_pattern, message)

    # Actualizar el contexto con los datos extraídos
    if email:
        context['email'] = email.group(0)
    if phone:
        context['phone'] = phone.group(0)
    if name:
        context['name'] = name.group(2).strip()
    if service:
        context['service'] = service.group(2).strip()

# Procesar mensajes del asistente
def handle_assistant_response(user_message, user_id):
    try:
        # Crear un hilo para el usuario si no existe
        if user_id not in user_threads:
            thread = client.beta.threads.create()
            user_threads[user_id] = thread.id
            user_context[user_id] = {}

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
        logger.info(f"Asistente: {assistant_message}")

        # Extraer datos del mensaje del usuario
        extract_user_data(user_message, user_context[user_id])

        # Verificar si tenemos todos los datos necesarios
        context = user_context[user_id]
        if all(key in context for key in ['name', 'email', 'phone', 'service']):
            org_id = create_organization(context['name'])
            if org_id:
                lead_id = create_lead(context['service'], org_id)
                if lead_id:
                    create_activity("Reunión inicial", "2025-01-15", "10:00", lead_id)
                    return "¡Lead creado exitosamente en Pipedrive!", None
            return "Error al crear el lead en Pipedrive.", None

        return assistant_message, None

    except Exception as e:
        logger.error(f"Error: {e}")
        return None, str(e)

if __name__ == "__main__":
    # Ejemplo de prueba
    user_message = "Hola, me llamo Juan Pérez, mi correo es juan.perez@ejemplo.com, mi número es 5551234567 y estoy buscando un servicio de consultoría."
    user_id = "12345"
    response, error = handle_assistant_response(user_message, user_id)
    if error:
        print(f"Error: {error}")
    else:
        print(f"Respuesta del asistente: {response}")
