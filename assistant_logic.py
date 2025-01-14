import re
from datetime import datetime
import pytz  # Asegúrate de instalar esta biblioteca: pip install pytz
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

    @override
    def on_text_created(self, text) -> None:
        self.assistant_message = text.value

    @override
    def on_text_delta(self, delta, snapshot):
        if not self.assistant_message.endswith(delta.value):
            self.assistant_message += delta.value


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
# Diccionario para almacenar la información del usuario y el estado del proceso
user_data = {}

def handle_assistant_response(user_message, user_id):
    try:
        # Si no hay información previa del usuario, iniciar un nuevo hilo
        if user_id not in user_threads:
            thread = client.beta.threads.create()
            user_threads[user_id] = thread.id
            user_data[user_id] = {"name": None, "phone": None, "email": None, "appointment_date": None, "appointment_time": None, "lead_created": False}

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

        # Extraer información del mensaje
        contact_name, contact_phone, contact_email = extract_user_info(user_message)
        activity_due_date = "2025-01-15"  # Simula un valor válido para pruebas
        activity_due_time = "15:00"  # Simula un valor válido para pruebas

        # Actualizamos los datos del usuario
        user_data[user_id]["name"] = contact_name or user_data[user_id]["name"]
        user_data[user_id]["phone"] = contact_phone or user_data[user_id]["phone"]
        user_data[user_id]["email"] = contact_email or user_data[user_id]["email"]
        user_data[user_id]["appointment_date"] = activity_due_date
        user_data[user_id]["appointment_time"] = activity_due_time

        # Comprobamos si se tiene toda la información necesaria
        if all(user_data[user_id].values()) and not user_data[user_id]["lead_created"]:
            # Si la información está completa, creamos el contacto, el lead y la cita
            contact_id = create_patient_contact(user_data[user_id]["name"], phone=user_data[user_id]["phone"], email=user_data[user_id]["email"])
            if contact_id:
                lead_id = create_patient_lead(contact_id, f"Lead para {user_data[user_id]['name']}", get_owner_id())
                if lead_id:
                    create_dental_appointment(
                        lead_id,
                        f'Cita de Revisión dental para {user_data[user_id]["name"]}',
                        "meeting",
                        user_data[user_id]["appointment_date"],
                        user_data[user_id]["appointment_time"],
                        "00:30",
                        "Tipo de tratamiento: Revisión dental",
                    )
                    user_data[user_id]["lead_created"] = True
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