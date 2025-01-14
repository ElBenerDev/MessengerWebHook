import re
import requests
from datetime import datetime
import pytz
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

# Datos de autenticación para Pipedrive
PIPEDRIVE_API_KEY = '8f2492eead4201ac69582ee4f3dfefd13d818b79'
COMPANY_DOMAIN = 'companiademuestra'

# Zona horaria de Argentina
ARGENTINA_TZ = pytz.timezone('America/Argentina/Buenos_Aires')

# Año fijo
FIXED_YEAR = 2025

# Función para convertir horario de Argentina a UTC
def convert_to_utc(date_str, time_str):
    local_time = ARGENTINA_TZ.localize(datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M"))
    utc_time = local_time.astimezone(pytz.utc)
    return utc_time.strftime("%H:%M")

# Función para obtener el ID del propietario dinámicamente
def get_owner_id():
    url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/users?api_token={PIPEDRIVE_API_KEY}'
    response = requests.get(url)
    if response.status_code == 200:
        users_data = response.json().get('data', [])
        for user in users_data:
            if user.get('active_flag') == 1:
                return user['id']
    logger.error(f"Error al obtener el ID del propietario: {response.status_code}")
    return None

# Función para crear contacto
def create_patient_contact(contact_name, phone=None, email=None):
    contact_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/persons?api_token={PIPEDRIVE_API_KEY}'
    contact_data = {'name': contact_name, 'phone': phone, 'email': email}
    response = requests.post(contact_url, json=contact_data)
    if response.status_code == 201:
        return response.json().get('data', {}).get('id')
    logger.error(f"Error al crear el contacto: {response.status_code}")
    return None

# Función para crear lead
def create_patient_lead(contact_id, lead_title, lead_owner_id):
    lead_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/leads?api_token={PIPEDRIVE_API_KEY}'
    lead_data = {'title': lead_title, 'person_id': contact_id, 'owner_id': lead_owner_id}
    response = requests.post(lead_url, json=lead_data)
    if response.status_code == 201:
        return response.json().get('data', {}).get('id')
    logger.error(f"Error al crear el lead: {response.status_code}")
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
    if response.status_code == 201:
        logger.info("Cita dental creada exitosamente!")
    else:
        logger.error(f"Error al crear la cita dental: {response.status_code}")

# Manejador de eventos para el asistente
class EventHandler(AssistantEventHandler):
    def __init__(self):
        super().__init__()
        self.assistant_message = ""
        self.user_data = {}  # Diccionario para almacenar la información del usuario

    @override
    def on_text_created(self, text) -> None:
        self.assistant_message = text.value

    @override
    def on_text_delta(self, delta, snapshot):
        if not self.assistant_message.endswith(delta.value):
            self.assistant_message += delta.value

    def store_user_info(self, message):
        # Aquí extraemos los datos del mensaje con expresiones regulares
        contact_name, contact_phone, contact_email = extract_user_info(message)

        # Si tenemos nombre, teléfono y correo, los almacenamos
        if contact_name:
            self.user_data['contact_name'] = contact_name
        if contact_phone:
            self.user_data['contact_phone'] = contact_phone
        if contact_email:
            self.user_data['contact_email'] = contact_email

        # Si tenemos la fecha y la hora de la cita, la almacenamos
        date_time_match = re.search(r"(\d{4}-\d{2}-\d{2})\s(\d{2}:\d{2})", message)
        if date_time_match:
            self.user_data['activity_due_date'] = date_time_match.group(1)
            self.user_data['activity_due_time'] = date_time_match.group(2)

    def create_lead_and_appointment(self):
        # Validamos si tenemos toda la información
        if all(key in self.user_data for key in ['contact_name', 'contact_phone', 'contact_email', 'activity_due_date', 'activity_due_time']):
            contact_name = self.user_data['contact_name']
            contact_phone = self.user_data['contact_phone']
            contact_email = self.user_data['contact_email']
            activity_due_date = self.user_data['activity_due_date']
            activity_due_time = self.user_data['activity_due_time']

            # Creamos el contacto, lead y cita
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
                    return "Cita agendada exitosamente."
                else:
                    return "Hubo un error al crear el lead."
            else:
                return "Hubo un error al crear el contacto."
        else:
            return "Falta información, por favor completa todos los datos."

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

# Procesar respuesta del asistente y registrar cita
def handle_assistant_response(user_message, user_id):
    try:
        if user_id not in user_threads:
            thread = client.beta.threads.create()
            user_threads[user_id] = thread.id

        client.beta.threads.messages.create(
            thread_id=user_threads[user_id],
            role="user",
            content=user_message,
        )

        event_handler = EventHandler()
        with client.beta.threads.runs.stream(
            thread_id=user_threads[user_id],
            assistant_id=assistant_id,
            event_handler=event_handler,
        ) as stream:
            stream.until_done()

        assistant_message = event_handler.assistant_message.strip()
        logger.info(f"Mensaje del asistente: {assistant_message}")

        # Almacenamos la información del usuario
        event_handler.store_user_info(user_message)

        # Creamos el lead y la cita cuando tengamos toda la información
        result_message = event_handler.create_lead_and_appointment()

        return assistant_message, result_message

    except Exception as e:
        logger.error(f"Error al procesar el mensaje: {e}")
        return None, f"Error interno: {e}"

# Ejemplo de uso
if __name__ == "__main__":
    user_message = "Hola, soy Bernardo Ramirez, mi teléfono es +54 9 11 2345 6789 y mi correo es bernardo@example.com. Quiero agendar una cita para el 2025-01-15 a las 15:00."
    response, result = handle_assistant_response(user_message, "user_123")
    if result:
        print(f"Resultado: {result}")
    else:
        print(f"Respuesta del asistente: {response}")
