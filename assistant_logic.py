import re
from datetime import datetime
import pytz
import requests
from openai import OpenAI
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

# Datos de autenticación para Pipedrive
PIPEDRIVE_API_KEY = '8f2492eead4201ac69582ee4f3dfefd13d818b79'
COMPANY_DOMAIN = 'companiademuestra'

# Zona horaria de Argentina
ARGENTINA_TZ = pytz.timezone('America/Argentina/Buenos_Aires')

# Año fijo
FIXED_YEAR = 2025

# Variables de datos de usuario
contact_name = None
contact_phone = None
contact_email = None
activity_due_date = "2025-01-15"  # Fecha fija de la cita
activity_due_time = "15:00"  # Hora fija para la cita
appointment_duration = "00:30"  # Duración de la cita
activity_note = "Tipo de tratamiento: Revisión dental"  # Nota de la cita

# Función para convertir horario de Argentina a UTC
def convert_to_utc(date_str, time_str):
    local_time = ARGENTINA_TZ.localize(datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M"))
    utc_time = local_time.astimezone(pytz.utc)
    return utc_time.strftime("%H:%M")

# Función para obtener el ID del propietario dinámicamente
def get_owner_id():
    url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/users?api_token={PIPEDRIVE_API_KEY}'
    response = requests.get(url)
    logger.info(f"Respuesta de obtener ID del propietario: {response.status_code}, {response.text}")
    if response.status_code == 200:
        users_data = response.json().get('data', [])
        for user in users_data:
            if user.get('active_flag') == 1:
                return user['id']
    logger.error(f"Error al obtener el ID del propietario: {response.status_code}, {response.text}")
    return None

# Función para crear contacto
def create_patient_contact(contact_name, phone=None, email=None):
    contact_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/persons?api_token={PIPEDRIVE_API_KEY}'
    contact_data = {'name': contact_name, 'phone': phone, 'email': email}
    response = requests.post(contact_url, json=contact_data)
    logger.info(f"Respuesta de crear contacto: {response.status_code}, {response.text}")
    if response.status_code == 201:
        return response.json().get('data', {}).get('id')
    logger.error(f"Error al crear el contacto: {response.status_code}, {response.text}")
    return None

# Función para crear lead
def create_patient_lead(contact_id, lead_title, lead_owner_id):
    lead_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/leads?api_token={PIPEDRIVE_API_KEY}'
    lead_data = {'title': lead_title, 'person_id': contact_id, 'owner_id': lead_owner_id}
    response = requests.post(lead_url, json=lead_data)
    logger.info(f"Respuesta de crear lead: {response.status_code}, {response.text}")
    if response.status_code == 201:
        return response.json().get('data', {}).get('id')
    logger.error(f"Error al crear el lead: {response.status_code}, {response.text}")
    return None

# Función para crear cita dental
def create_dental_appointment(lead_id, activity_subject, activity_type, activity_due_date, activity_due_time, activity_duration, activity_note):
    activity_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/activities?api_token={PIPEDRIVE_API_KEY}'
    utc_due_time = convert_to_utc(activity_due_date, activity_due_time)
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
    logger.info(f"Respuesta de crear cita dental: {response.status_code}, {response.text}")
    if response.status_code == 201:
        logger.info("Cita dental creada exitosamente!")
    else:
        logger.error(f"Error al crear la cita dental: {response.status_code}, {response.text}")

# Función para extraer información del mensaje del usuario
def extract_user_info(user_message):
    # Expresiones regulares para extraer nombre, teléfono y correo
    name_pattern = r"([A-Za-záéíóúÁÉÍÓÚ]+(?: [A-Za-záéíóúÁÉÍÓÚ]+)*)"
    phone_pattern = r"\(?\+?\d{1,3}\)?[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}"
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

    # Buscar nombre, teléfono y correo
    name_match = re.search(name_pattern, user_message)
    phone_match = re.search(phone_pattern, user_message)
    email_match = re.search(email_pattern, user_message)

    # Extraer los valores si están presentes
    contact_name = name_match.group(0) if name_match else None
    contact_phone = phone_match.group(0) if phone_match else None
    contact_email = email_match.group(0) if email_match else None

    return contact_name, contact_phone, contact_email

# Definir el manejador de eventos
class EventHandler:
    def __init__(self):
        self.assistant_message = None

    def handle_message(self, message):
        self.assistant_message = message['text']

# Lógica para procesar la respuesta del asistente y crear la cita
def handle_assistant_response(user_message, user_id):
    global contact_name, contact_phone, contact_email, activity_due_date, activity_due_time

    try:
        # Si no hay información previa del usuario, iniciar un nuevo hilo
        if user_id not in user_threads:
            thread = client.beta.threads.create()
            user_threads[user_id] = thread.id

        client.beta.threads.messages.create(
            thread_id=user_threads[user_id],
            role="user",
            content=user_message,
        )

        event_handler = EventHandler()

        # Aquí se está manejando el flujo del asistente
        with client.beta.threads.runs.stream(
            thread_id=user_threads[user_id],
            assistant_id=assistant_id,
            event_handler=event_handler,
        ) as stream:
            stream.until_done()

        assistant_message = event_handler.assistant_message.strip()
        logger.info(f"Mensaje del asistente: {assistant_message}")

        # Extraer información del mensaje
        contact_name, contact_phone, contact_email = extract_user_info(user_message)

        # Verificar si la información está completa
        if contact_name and contact_phone and contact_email:
            contact_id = create_patient_contact(contact_name, phone=contact_phone, email=contact_email)
            if contact_id:
                lead_id = create_patient_lead(contact_id, f"Lead para {contact_name}", get_owner_id())
                if lead_id:
                    create_dental_appointment(
                        lead_id,
                        f'Cita de Revisión dental para {contact_name}',
                        "meeting",
                        activity_due_date,
                        activity_due_time,
                        "00:30",
                        "Tipo de tratamiento: Revisión dental",
                    )
                    logger.info("Lead y cita creados exitosamente!")
                    return assistant_message, None
            else:
                logger.error("No se pudo crear el contacto.")
                return assistant_message, "Hubo un problema al crear el contacto."
        else:
            logger.info("Esperando más información del usuario.")
            return assistant_message, None

    except ValueError as ve:
        logger.error(f"Error de validación: {ve}")
        return None, f"Hubo un problema con los datos proporcionados: {ve}"
    except Exception as e:
        logger.error(f"Error al procesar el mensaje: {e}")
        return None, f"Error interno: {e}"

# Ejemplo de uso
if __name__ == "__main__":
    user_message = "Hola, soy Bernardo Ramirez, mi teléfono es +54 9 11 2345 6789 y mi correo es bernardo@example.com. Quiero agendar una cita mañana por la tarde para una limpieza dental."
    response, error = handle_assistant_response(user_message, "user_123")
    if error:
        print(f"Error: {error}")
    else:
        print(f"Respuesta del asistente: {response}")
