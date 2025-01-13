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

# Diccionario para almacenar el thread_id de cada usuario
user_threads = {}

# Variables globales
contact_name = None
contact_phone = None
activity_due_date = None
activity_due_time = None
PIPEDRIVE_API_KEY = '8f2492eead4201ac69582ee4f3dfefd13d818b79'
COMPANY_DOMAIN = 'companiademuestra'

class EventHandler(AssistantEventHandler):
    def __init__(self):
        super().__init__()
        self.assistant_message = ""

    @override
    def on_text_created(self, text):
        if not self.assistant_message.endswith(text['text']):
            self.assistant_message += text['text']

    @override
    def on_text_delta(self, delta, snapshot):
        if not self.assistant_message.endswith(delta['text']):
            self.assistant_message += delta['text']

    def finalize_message(self):
        return self.assistant_message.strip()

def handle_assistant_response(user_message, user_id):
    """
    Procesa el mensaje del usuario y devuelve la respuesta generada por el asistente.
    """
    if not user_message or not user_id:
        logger.error("No se proporcionó un mensaje o ID de usuario válido.")
        return None, "No se proporcionó un mensaje o ID de usuario válido."

    logger.info(f"Mensaje recibido del usuario {user_id}: {user_message}")

    try:
        # Crear un hilo nuevo si no existe para el usuario
        if user_id not in user_threads:
            thread = client.beta.threads.create(assistant_id=assistant_id)
            user_threads[user_id] = thread['id']
            logger.info(f"Hilo creado para el usuario {user_id}: {thread['id']}")

        # Enviar mensaje al hilo existente
        client.beta.threads.messages.create(
            thread_id=user_threads[user_id],
            role="user",
            content=user_message
        )

        # Manejar la respuesta del asistente
        event_handler = EventHandler()
        with client.beta.threads.runs.stream(
            thread_id=user_threads[user_id],
            assistant_id=assistant_id,
            event_handler=event_handler,
        ) as stream:
            stream.until_done()

        assistant_message = event_handler.finalize_message()
        logger.info(f"Mensaje generado por el asistente: {assistant_message}")

        return assistant_message, None

    except Exception as e:
        logger.error(f"Error al procesar el mensaje: {e}")
        return None, f"Error al procesar el mensaje: {e}"

# Función para crear contacto
def create_patient_contact(contact_name, phone=None, email=None):
    contact_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/persons?api_token={PIPEDRIVE_API_KEY}'
    contact_data = {
        'name': contact_name,
    }
    if phone:
        contact_data['phone'] = phone
    if email:
        contact_data['email'] = email

    response = requests.post(contact_url, json=contact_data)
    if response.status_code == 201:
        contact = response.json()
        return contact['data']['id']
    return None

# Función para crear lead
def create_patient_lead(contact_id, lead_title, lead_owner_id):
    lead_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/leads?api_token={PIPEDRIVE_API_KEY}'
    lead_data = {
        'title': lead_title,
        'person_id': contact_id,
        'owner_id': lead_owner_id,
    }

    response = requests.post(lead_url, json=lead_data)
    if response.status_code == 201:
        lead = response.json()
        return lead['data']['id']
    else:
        logger.error(f"Error al crear el lead: {response.status_code}")
        logger.error(response.text)
    return None

# Verificar actividades existentes
def check_existing_appointments(due_date, due_time, duration):
    activity_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/activities?api_token={PIPEDRIVE_API_KEY}'
    response = requests.get(activity_url)
    if response.status_code == 200:
        activities = response.json().get('data', [])
        for activity in activities:
            if activity['due_date'] == due_date and activity['due_time'] == due_time:
                return True  # Ya existe una actividad en ese horario
    return False

# Validar si está dentro del horario laboral
def is_within_working_hours(activity_due_time):
    WORKING_HOURS_START = "09:00"
    WORKING_HOURS_END = "18:00"
    return WORKING_HOURS_START <= activity_due_time <= WORKING_HOURS_END

# Crear cita dental
def create_dental_appointment(lead_id, activity_subject, activity_type, activity_due_date, activity_due_time, activity_duration, activity_note):
    ARGENTINA_TZ = pytz.timezone("America/Argentina/Buenos_Aires")
    
    local_time = ARGENTINA_TZ.localize(datetime.strptime(f"{activity_due_date} {activity_due_time}", "%Y-%m-%d %H:%M"))
    utc_time = local_time.astimezone(pytz.utc)
    utc_due_time = utc_time.strftime("%H:%M")

    if not is_within_working_hours(activity_due_time):
        logger.error("La cita está fuera del horario laboral.")
        return

    if check_existing_appointments(activity_due_date, utc_due_time, activity_duration):
        logger.error("Ya existe una actividad en ese horario.")
        return

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

# Flujo principal para crear cita y lead
def create_appointment_and_lead():
    if contact_name and contact_phone:
        contact_id = create_patient_contact(contact_name, phone=contact_phone)

        if contact_id:
            lead_id = create_patient_lead(contact_id, f"Lead para {contact_name}", lead_owner_id=23104380)

            if lead_id and activity_due_date and activity_due_time:
                create_dental_appointment(
                    lead_id,
                    activity_subject=f'Cita de Revisión dental para {contact_name}',
                    activity_type="meeting",
                    activity_due_date=activity_due_date,
                    activity_due_time=activity_due_time,
                    activity_duration="00:30",
                    activity_note="Tipo de tratamiento: Revisión dental"
                )

# Flujo de prueba
if __name__ == "__main__":
    user_message = "Juan Pérez"
    user_id = "1234"
    handle_assistant_response(user_message, user_id)

    user_message = "+1234567890"
    handle_assistant_response(user_message, user_id)

    user_message = "2025-01-15 09:00"
    handle_assistant_response(user_message, user_id)

    create_appointment_and_lead()
