from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import logging
import os
import requests
from datetime import datetime
import pytz

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración del cliente OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ID del asistente
assistant_id = os.getenv("ASSISTANT_ID", "asst_d2QBbmcrr6vdZgxusPdqNOtY")

# Diccionario para almacenar los hilos por usuario
user_threads = {}

# Configuración de Pipedrive
PIPEDRIVE_API_KEY = os.getenv("PIPEDRIVE_API_KEY", "your_pipedrive_api_key")
COMPANY_DOMAIN = os.getenv("COMPANY_DOMAIN", "your_company_domain")

# Zona horaria de Argentina
ARGENTINA_TZ = pytz.timezone("America/Argentina/Buenos_Aires")

# Definición del horario laboral
WORKING_HOURS_START = "09:00"
WORKING_HOURS_END = "18:00"

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

# Función para convertir horario de Argentina a UTC
def convert_to_utc(date_str, time_str):
    local_time = ARGENTINA_TZ.localize(datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M"))
    utc_time = local_time.astimezone(pytz.utc)
    return utc_time.strftime("%H:%M")

# Función para validar si el horario está dentro del horario laboral
def is_within_working_hours(activity_due_time):
    return WORKING_HOURS_START <= activity_due_time <= WORKING_HOURS_END

# Función para crear contacto
def create_patient_contact(contact_name, phone=None, email=None):
    logger.info(f"Creando contacto para: {contact_name}")
    contact_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/persons?api_token={PIPEDRIVE_API_KEY}'
    contact_data = {'name': contact_name}
    if phone:
        contact_data['phone'] = phone
    if email:
        contact_data['email'] = email

    response = requests.post(contact_url, json=contact_data)
    if response.status_code == 201:
        contact = response.json()
        logger.info(f"Contacto creado exitosamente: {contact['data']['id']}")
        return contact['data']['id']
    else:
        logger.error(f"Error al crear el contacto: {response.status_code}")
        logger.error(response.text)
    return None

# Función para crear lead
def create_patient_lead(contact_id, lead_title, lead_owner_id):
    logger.info(f"Creando lead para el contacto {contact_id} con título '{lead_title}'")
    lead_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/leads?api_token={PIPEDRIVE_API_KEY}'
    lead_data = {
        'title': lead_title,
        'person_id': contact_id,
        'owner_id': lead_owner_id,
    }

    response = requests.post(lead_url, json=lead_data)
    if response.status_code == 201:
        lead = response.json()
        logger.info(f"Lead creado exitosamente: {lead['data']['id']}")
        return lead['data']['id']
    else:
        logger.error(f"Error al crear el lead: {response.status_code}")
        logger.error(response.text)
    return None

# Función para verificar actividades existentes
def check_existing_appointments(due_date, due_time):
    logger.info(f"Verificando actividades existentes para la fecha {due_date} y hora {due_time}")
    activity_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/activities?api_token={PIPEDRIVE_API_KEY}'
    response = requests.get(activity_url)
    if response.status_code == 200:
        activities = response.json().get('data', [])
        for activity in activities:
            if activity['due_date'] == due_date and activity['due_time'] == due_time:
                logger.info("Ya existe una actividad programada para ese horario.")
                return True
    logger.info("No se encontró ninguna actividad en ese horario.")
    return False

# Función para crear cita dental
def create_dental_appointment(lead_id, activity_subject, activity_type, activity_due_date, activity_due_time, activity_duration, activity_note):
    utc_due_time = convert_to_utc(activity_due_date, activity_due_time)

    if not is_within_working_hours(activity_due_time):
        logger.warning("La cita no se puede crear porque está fuera del horario laboral.")
        return

    if check_existing_appointments(activity_due_date, utc_due_time):
        logger.warning("La cita no se puede crear porque ya hay una actividad programada en ese horario.")
        return

    logger.info(f"Creando cita dental para el lead {lead_id}")
    activity_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/activities?api_token={PIPEDRIVE_API_KEY}'
    activity_data = {
        'subject': activity_subject,
        'type': activity_type,
        'due_date': activity_due_date,
        'due_time': utc_due_time,
        'duration': activity_duration,
        'lead_id': lead_id,
        'note': activity_note,
    }

    response = requests.post(activity_url, json=activity_data)
    if response.status_code == 201:
        logger.info("Cita dental creada exitosamente!")
    else:
        logger.error(f"Error al crear la cita dental: {response.status_code}")
        logger.error(response.text)

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
        return assistant_message, None

    except Exception as e:
        logger.error(f"Error al procesar el mensaje: {str(e)}")
        return None, f"Error al procesar el mensaje: {str(e)}"
