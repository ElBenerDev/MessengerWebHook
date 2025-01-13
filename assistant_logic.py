import requests
import logging
import os
import re
from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración del cliente OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ID del asistente
assistant_id = os.getenv("ASSISTANT_ID", "asst_d2QBbmcrr6vdZgxusPdqNOtY")

# Datos de autenticación Pipedrive (valores directamente en el código)
PIPEDRIVE_API_KEY = "8f2492eead4201ac69582ee4f3dfefd13d818b79"
COMPANY_DOMAIN = "companiademuestra"

# Diccionario para almacenar los hilos y contexto por usuario
user_threads = {}
user_context = {}

# Crear una organización en Pipedrive
def create_organization(name):
    logger.info(f"Creando organización con el nombre: {name}")
    # URL de organización con los valores directamente en el código
    organization_url = 'https://companiademuestra.pipedrive.com/v1/organizations?api_token=8f2492eead4201ac69582ee4f3dfefd13d818b79'
    organization_data = {'name': name}
    response = requests.post(organization_url, json=organization_data)
    logger.debug(f"Respuesta al crear organización: {response.text}")
    if response.status_code == 201:
        organization = response.json()
        logger.info(f"Organización creada con éxito. ID: {organization['data']['id']}")
        return organization['data']['id']
    else:
        logger.error(f"Error al crear la organización: {response.text}")
        return None

# Crear un lead en Pipedrive
def create_lead(title, organization_id):
    logger.info(f"Creando lead con título: {title} para la organización ID: {organization_id}")
    # URL de lead con los valores directamente en el código
    lead_url = 'https://companiademuestra.pipedrive.com/v1/leads?api_token=8f2492eead4201ac69582ee4f3dfefd13d818b79'
    lead_data = {'title': title, 'organization_id': organization_id}
    response = requests.post(lead_url, json=lead_data)
    logger.debug(f"Respuesta al crear lead: {response.text}")
    if response.status_code == 201:
        lead = response.json()
        logger.info(f"Lead creado con éxito. ID: {lead['data']['id']}")
        return lead['data']['id']
    else:
        logger.error(f"Error al crear el lead: {response.text}")
        return None

# Crear una actividad en Pipedrive
def create_activity(subject, due_date, due_time, lead_id):
    logger.info(f"Creando actividad con el asunto: {subject} para el lead ID: {lead_id}")
    # URL de actividad con los valores directamente en el código
    activity_url = 'https://companiademuestra.pipedrive.com/v1/activities?api_token=8f2492eead4201ac69582ee4f3dfefd13d818b79'
    activity_data = {
        'subject': subject,
        'type': 'meeting',
        'due_date': due_date,
        'due_time': due_time,
        'duration': '01:00',
        'lead_id': lead_id,
    }
    response = requests.post(activity_url, json=activity_data)
    logger.debug(f"Respuesta al crear actividad: {response.text}")
    if response.status_code == 201:
        logger.info("Actividad creada exitosamente!")
    else:
        logger.error(f"Error al crear la actividad: {response.text}")

# Extraer datos clave del mensaje del usuario
def extract_user_data(message, context):
    logger.info(f"Extrayendo datos del mensaje: {message}")
    # Patrones de extracción de datos
    email_pattern = r"[\w\.-]+@[\w\.-]+\.\w+"
    phone_pattern = r"\b\d{10}\b|\b\d{7}\b|\+?\d[\d\s-]{8,}\d"
    name_pattern = r"(?i)(mi nombre es|soy|me llamo)\s([\w\s]+)"
    service_pattern = r"(?i)(busco|necesito|quiero)\s([\w\s]+)"
    date_pattern = r"(\d{1,2} de \w+ de \d{4})"  # Para la fecha (ej. 13 de enero de 2025)
    time_pattern = r"(\d{1,2}:\d{2} (AM|PM))"  # Para la hora (ej. 5:00 PM)

    # Extraer datos según patrones
    email = re.search(email_pattern, message)
    phone = re.search(phone_pattern, message)
    name = re.search(name_pattern, message)
    service = re.search(service_pattern, message)
    date = re.search(date_pattern, message)
    time = re.search(time_pattern, message)

    # Actualizar el contexto con los datos extraídos
    if email:
        context['email'] = email.group(0)
    if phone:
        context['phone'] = phone.group(0)
    if name:
        context['name'] = name.group(2).strip()
    if service:
        context['service'] = service.group(2).strip()
    if date:
        context['date'] = date.group(0)
    if time:
        context['time'] = time.group(0)

# Procesar mensajes del asistente y crear registros en Pipedrive
# Procesar mensajes del asistente y crear registros en Pipedrive
def handle_assistant_response(user_message, user_id):
    try:
        logger.info(f"Procesando mensaje del usuario: {user_message} para el usuario ID: {user_id}")
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
        if all(key in context for key in ['name', 'email', 'phone', 'service', 'date', 'time']):
            logger.info(f"Todos los datos necesarios están disponibles: {context}")

            # Crear la organización en Pipedrive
            org_id = create_organization(context['name'])
            if org_id:
                # Crear el lead en Pipedrive
                lead_id = create_lead(f"{context['service']} - {context['name']}", org_id)
                if lead_id:
                    # Crear la actividad en Pipedrive
                    create_activity(context['service'], context['date'], context['time'], lead_id)
                    return "¡Lead y cita creados exitosamente en Pipedrive!", None
            return "Error al crear el lead y la cita en Pipedrive.", None

        # Si no tenemos todos los datos, devolver el mensaje del asistente
        return assistant_message, None

    except Exception as e:
        logger.error(f"Error en la función handle_assistant_response: {e}")
        return None, str(e)



# Evento para manejar el stream de respuestas del asistente
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

if __name__ == "__main__":
    # Ejemplo de prueba
    user_message = "Hola, me llamo Manuel, mi correo es bernardorao90@gmail.com, mi número es 4426693885, busco una limpieza dental el 13 de enero de 2025 a las 5:00 PM."
    user_id = "5214426693885"
    response, error = handle_assistant_response(user_message, user_id)
    if response:
        print(response)
    if error:
        print(f"Error: {error}")
