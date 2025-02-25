from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import logging
import os
import re
from datetime import datetime
import pytz
import requests

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

# Función para extraer información del mensaje del usuario
def extract_user_info(user_message):
    # Modificamos el patrón del nombre para que extraiga correctamente el nombre después de "soy"
    name_pattern = r"(?<=soy\s)([A-Za-záéíóúÁÉÍÓÚ]+(?: [A-Za-záéíóúÁÉÍÓÚ]+)*)"
    phone_pattern = r"\(?\+?\d{1,3}\)?[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}"
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

    name_match = re.search(name_pattern, user_message)
    phone_match = re.search(phone_pattern, user_message)
    email_match = re.search(email_pattern, user_message)

    contact_name = name_match.group(0) if name_match else None
    contact_phone = phone_match.group(0) if phone_match else None
    contact_email = email_match.group(0) if email_match else None

    return contact_name, contact_phone, contact_email

# Función para crear un nuevo contacto en Pipedrive
def create_pipedrive_contact(contact_name, contact_phone, contact_email):
    url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/persons?api_token={PIPEDRIVE_API_KEY}'
    headers = {
        'Content-Type': 'application/json',
    }
    data = {
        'name': contact_name,
        'phone': contact_phone,
        'email': contact_email,
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        contact_id = response.json().get('data', {}).get('id')
        logger.info(f"Contacto creado exitosamente para {contact_name}")
        return contact_id
    else:
        logger.error(f"Error al crear el contacto: {response.text}")
        return None

# Función para crear un nuevo lead en Pipedrive
def create_pipedrive_lead(contact_id, service, date, time):
    url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/leads?api_token={PIPEDRIVE_API_KEY}'
    headers = {
        'Content-Type': 'application/json',
    }

    # Convertir la fecha en formato YYYY-MM-DD
    try:
        formatted_date = datetime.strptime(date, "%d de %B").strftime("%Y-%m-%d")
    except ValueError as e:
        logger.error(f"Error al formatear la fecha: {e}")
        return None
    
    # Asegurarse de que la hora esté en formato adecuado
    try:
        formatted_time = datetime.strptime(time, "%H:%M").strftime("%H:%M")
    except ValueError as e:
        logger.error(f"Error al formatear la hora: {e}")
        return None

    data = {
        'title': f"Cita para {service}",  # Usamos el servicio para el título del lead
        'person_id': contact_id,  # El ID del contacto
        'date': formatted_date,  # Fecha de la cita
        'time': formatted_time,  # Hora de la cita
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Asegura que se manejen los errores HTTP
        if response.status_code == 201:
            logger.info(f"Lead creado exitosamente para {service}")
            return response.json()
        else:
            logger.error(f"Error al crear el lead: {response.json()}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error de conexión al crear el lead: {e}")
        return None

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

def handle_assistant_response(user_message, user_id):
    try:
        # Crear un nuevo hilo si no existe
        if user_id not in user_threads:
            thread = client.beta.threads.create()
            logger.info(f"Hilo creado para el usuario {user_id}: {thread.id}")
            user_threads[user_id] = thread.id

        thread_id = user_threads[user_id]

        # Verificar si hay una ejecución activa en el hilo
        active_runs = client.beta.threads.runs.list(thread_id=thread_id)
        if active_runs and active_runs.data:
            for run in active_runs.data:
                if run.status != "completed":
                    run_id = run.id
                    logger.warning(f"Ejecutando run {run_id} en hilo {thread_id}. Intentando cancelar...")
                    try:
                        client.beta.threads.runs.cancel(run_id=run_id, thread_id=thread_id)
                        logger.info(f"Run {run_id} cancelado exitosamente.")
                    except Exception as cancel_error:
                        logger.error(f"No se pudo cancelar el run {run_id}: {cancel_error}")
                else:
                    logger.info(f"El run {run.id} ya está completado, no se requiere cancelación.")



        # Enviar el mensaje del usuario al hilo existente
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
        )

        # Crear un manejador de eventos
        event_handler = EventHandler()
        with client.beta.threads.runs.stream(
            thread_id=thread_id,
            assistant_id=assistant_id,
            event_handler=event_handler,
        ) as stream:
            stream.until_done()

        assistant_message = event_handler.assistant_message.strip()
        logger.info(f"Mensaje generado por el asistente: {assistant_message}")

        # Procesar información del usuario
        contact_name, contact_phone, contact_email = extract_user_info(user_message)

        if contact_name and contact_phone and contact_email:
            logger.info(f"Datos extraídos: Nombre: {contact_name}, Teléfono: {contact_phone}, Correo: {contact_email}")
            service_pattern = r"servicio:\s*([A-Za-z\s]+)"
            date_pattern = r"(\d{1,2} de \w+)"
            service_match = re.search(service_pattern, user_message, re.IGNORECASE)
            date_match = re.search(date_pattern, user_message)

            service = service_match.group(1) if service_match else "Servicio no especificado"
            date_str = date_match.group(1) if date_match else "Fecha no especificada"
            time_str = "10:00"  # Asumimos una hora predeterminada si no se encuentra

            contact_id = create_pipedrive_contact(contact_name, contact_phone, contact_email)
            if contact_id:
                create_pipedrive_lead(contact_id, service, date_str, time_str)

        return assistant_message, None

    except Exception as e:
        logger.error(f"Error al procesar el mensaje: {str(e)}")
        return None, f"Error al procesar el mensaje: {str(e)}"


# Ejemplo de uso
if __name__ == "__main__":
    user_message = "Hola, soy Claudia, mi teléfono es 1234567890 y mi correo es jsjd@gmail.com. Quiero agendar una cita para una limpieza dental el 16 de enero a las 10:00."
    response, error = handle_assistant_response(user_message, "user_123")
    if error:
        print(f"Error: {error}")
    else:
        print(f"Respuesta del asistente: {response}")
