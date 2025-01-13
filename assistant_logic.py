import openai
import logging
import os
import requests
from datetime import datetime
import pytz

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configura tu cliente con la API key desde el entorno
openai.api_key = os.getenv("OPENAI_API_KEY")

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

class EventHandler:
    def __init__(self):
        self.assistant_message = ""
        self.message_complete = False

    def on_text_created(self, text):
        if not self.message_complete and text['text'] not in self.assistant_message:
            self.assistant_message += text['text']

    def on_text_delta(self, delta, snapshot):
        if not self.message_complete and delta['text'] not in self.assistant_message:
            self.assistant_message += delta['text']

    def finalize_message(self):
        if not self.message_complete:
            self.message_complete = True
        return self.assistant_message.strip()

def handle_assistant_response(user_message, user_id):
    global contact_name, contact_phone, activity_due_date, activity_due_time
    if not user_message or not user_id:
        logger.error("No se proporcionó un mensaje o ID de usuario válido.")
        return None, "No se proporcionó un mensaje o ID de usuario válido."

    logger.info(f"Mensaje recibido del usuario {user_id}: {user_message}")

    try:
        # Verificar si ya existe un hilo para este usuario
        if user_id not in user_threads:
            user_threads[user_id] = []  # Iniciar un nuevo hilo para este usuario

        # Agregar el mensaje del usuario al hilo de conversación
        user_threads[user_id].append({"role": "user", "content": user_message})

        # Crear y manejar la respuesta del asistente
        event_handler = EventHandler()

        # Usar OpenAI ChatCompletion para obtener respuestas del asistente
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Ajustar al modelo que estés usando
            messages=user_threads[user_id]
        )

        assistant_message = response['choices'][0]['message']['content'].strip()
        logger.info(f"Mensaje generado por el asistente: {assistant_message}")

        # Añadir la respuesta al hilo del usuario
        user_threads[user_id].append({"role": "assistant", "content": assistant_message})

        # Procesar la respuesta del asistente para almacenar datos
        if "¿Cuál es el nombre del paciente?" in assistant_message:
            contact_name = user_message
        elif "¿Cuál es el teléfono?" in assistant_message:
            contact_phone = user_message
        elif "¿Cuándo te gustaría agendar la cita?" in assistant_message:
            activity_due_date, activity_due_time = user_message.split(" ")  # Suponiendo que se ingresa en formato 'YYYY-MM-DD HH:MM'
        
        return assistant_message, None

    except Exception as e:
        logger.error(f"Error al generar respuesta: {e}")
        return None, f"Error al generar respuesta: {e}"

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
        print(f"Error al crear el lead: {response.status_code}")
        print(response.text)
    return None

# Función para verificar actividades existentes
def check_existing_appointments(due_date, due_time, duration):
    activity_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/activities?api_token={PIPEDRIVE_API_KEY}'
    response = requests.get(activity_url)
    if response.status_code == 200:
        activities = response.json().get('data', [])
        for activity in activities:
            if activity['due_date'] == due_date and activity['due_time'] == due_time:
                return True  # Ya existe una actividad en ese horario
    return False

# Función para validar si el horario está dentro del horario laboral
def is_within_working_hours(activity_due_time):
    WORKING_HOURS_START = "09:00"
    WORKING_HOURS_END = "18:00"
    return WORKING_HOURS_START <= activity_due_time <= WORKING_HOURS_END

# Función para crear cita dental (actividad)
def create_dental_appointment(lead_id, activity_subject, activity_type, activity_due_date, activity_due_time, activity_duration, activity_note):
    # Zona horaria de Argentina
    ARGENTINA_TZ = pytz.timezone("America/Argentina/Buenos_Aires")
    
    # Convertir horario de Argentina a UTC
    local_time = ARGENTINA_TZ.localize(datetime.strptime(f"{activity_due_date} {activity_due_time}", "%Y-%m-%d %H:%M"))
    utc_time = local_time.astimezone(pytz.utc)
    utc_due_time = utc_time.strftime("%H:%M")  # Devuelve solo la hora en formato UTC

    if not is_within_working_hours(activity_due_time):  # Verificar en hora local de Argentina
        print("La cita no se puede crear porque está fuera del horario laboral.")
        return

    if check_existing_appointments(activity_due_date, utc_due_time, activity_duration):
        print("La cita no se puede crear porque ya hay una actividad programada en ese horario.")
        return

    activity_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/activities?api_token={PIPEDRIVE_API_KEY}'
    activity_data = {
        'subject': activity_subject,
        'type': activity_type,
        'due_date': activity_due_date,
        'due_time': utc_due_time,  # Guardar en UTC en Pipedrive
        'duration': activity_duration,
        'lead_id': lead_id,
        'note': activity_note,
    }

    response = requests.post(activity_url, json=activity_data)
    if response.status_code == 201:
        print("Cita dental creada exitosamente!")
    else:
        print(f"Error al crear la cita dental: {response.status_code}")
        print(response.text)

# Función principal para crear cita y lead
def create_appointment_and_lead():
    # Paso 1: Crear un contacto para el paciente
    if contact_name and contact_phone:
        contact_id = create_patient_contact(contact_name, phone=contact_phone)

        # Paso 2: Crear el lead para el paciente
        if contact_id:
            lead_id = create_patient_lead(contact_id, "Lead para " + contact_name, lead_owner_id=23104380)  # Cambiar el owner_id si es necesario

            # Paso 3: Crear la cita dental para el paciente
            if lead_id and activity_due_date and activity_due_time:
                create_dental_appointment(
                    lead_id,
                    activity_subject=f'Cita de Revisión dental para {contact_name}',
                    activity_type="meeting",
                    activity_due_date=activity_due_date,
                    activity_due_time=activity_due_time,
                    activity_duration="00:30",  # Cambiar la duración si es necesario
                    activity_note="Tipo de tratamiento: Revisión dental"
                )

# Flujo principal para iniciar la interacción con el asistente
if __name__ == "__main__":
    # Simulamos interacción del usuario para permitir que el asistente manipule las variables
    user_message = "Juan Pérez"  # Ejemplo de respuesta de usuario
    user_id = "1234"  # ID de usuario para simulación
    handle_assistant_response(user_message, user_id)

    user_message = "+1234567890"  # Ejemplo de teléfono
    handle_assistant_response(user_message, user_id)

    user_message = "2025-01-15 09:00"  # Ejemplo de fecha y hora para la cita
    handle_assistant_response(user_message, user_id)

    # Ahora procederemos a crear la cita y el lead
    create_appointment_and_lead()
