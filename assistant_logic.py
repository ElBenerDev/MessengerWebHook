import requests
import logging
import os
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

# Diccionario para almacenar los hilos por usuario
user_threads = {}

# Datos de autenticación de Pipedrive
PIPEDRIVE_API_KEY = '8f2492eead4201ac69582ee4f3dfefd13d818b79'  # API token de Pipedrive
COMPANY_DOMAIN = 'companiademuestra'  # Dominio de tu cuenta de Pipedrive

# Crear una nueva organización en Pipedrive
def create_organization(name, email, phone):
    organization_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/organizations?api_token={PIPEDRIVE_API_KEY}'
    organization_data = {
        'name': name,  # Nombre de la organización
        'email': email,  # Correo electrónico de la organización
        'phone': phone  # Teléfono de la organización
    }
    response = requests.post(organization_url, json=organization_data)
    if response.status_code == 201:
        organization = response.json()
        organization_id = organization['data']['id']
        print(f"Organización creada exitosamente! ID: {organization_id}")
        return organization_id
    else:
        print(f"Error al crear la organización: {response.status_code}")
        print(response.text)
        return None

# Crear un nuevo lead asociado a la organización
def create_lead(title, organization_id, service, date_time):
    lead_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/leads?api_token={PIPEDRIVE_API_KEY}'
    lead_data = {
        'title': title,  # Título del lead (Nombre del cliente)
        'organization_id': organization_id,  # ID de la organización asociada
        'service': service,  # Servicio solicitado
        'due_date': date_time.split(' ')[0],  # Fecha de la actividad (formato YYYY-MM-DD)
        'due_time': date_time.split(' ')[1]  # Hora de la actividad (formato HH:MM)
    }
    response = requests.post(lead_url, json=lead_data)
    if response.status_code == 201:
        lead = response.json()
        lead_id = lead['data']['id']
        print(f"Lead creado exitosamente! ID: {lead_id}")
        return lead_id
    else:
        print(f"Error al crear el lead: {response.status_code}")
        print(response.text)
        return None

# Crear una actividad (cita) asociada al lead
def create_activity(subject, due_date, due_time, lead_id):
    activity_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/activities?api_token={PIPEDRIVE_API_KEY}'
    activity_data = {
        'subject': subject,  # Asunto de la actividad (Reunión inicial con cliente)
        'type': 'meeting',  # Tipo de actividad
        'due_date': due_date,  # Fecha de la actividad (formato YYYY-MM-DD)
        'due_time': due_time,  # Hora de la actividad (formato HH:MM)
        'duration': '01:00',  # Duración de la actividad (en formato HH:MM)
        'lead_id': lead_id  # ID del lead asociado a la actividad
    }
    response = requests.post(activity_url, json=activity_data)
    if response.status_code == 201:
        print("Actividad creada exitosamente!")
        print(response.json())
    else:
        print(f"Error al crear la actividad: {response.status_code}")
        print(response.text)

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

# Lógica principal del asistente
def handle_assistant_response(user_message, user_id):
    """
    Procesa el mensaje del usuario y devuelve una respuesta generada por el asistente.
    :param user_message: str, mensaje del usuario
    :param user_id: str, identificador único del usuario
    :return: (str, str | None) respuesta generada, error (si ocurre)
    """
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

        # Verificamos si el mensaje contiene toda la información necesaria
        if 'nombre' in assistant_message and 'teléfono' in assistant_message and 'correo' in assistant_message and 'servicio' in assistant_message:
            # Extraemos la información relevante (esto es solo un ejemplo)
            name = "Nombre extraído"
            email = "Correo extraído"
            phone = "Teléfono extraído"
            service = "Servicio extraído"
            date_time = "Fecha y hora extraída"

            # Llamamos a las funciones de Pipedrive
            organization_id = create_organization(name, email, phone)
            if organization_id:
                lead_id = create_lead(name, organization_id, service, date_time)
                if lead_id:
                    activity_subject = service
                    activity_due_date = date_time.split(' ')[0]
                    activity_due_time = date_time.split(' ')[1]
                    create_activity(activity_subject, activity_due_date, activity_due_time, lead_id)

        return assistant_message, None

    except Exception as e:
        logger.error(f"Error al procesar el mensaje: {str(e)}")
        return None, f"Error al procesar el mensaje: {str(e)}"

# Simulación de mensaje de usuario y procesamiento
if __name__ == "__main__":
    user_message = "Información sobre servicio de limpieza dental"
    user_id = "usuario123"
    handle_assistant_response(user_message, user_id)
