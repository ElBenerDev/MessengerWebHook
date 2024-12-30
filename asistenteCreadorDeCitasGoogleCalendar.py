from flask import Flask, request, jsonify
from openai import OpenAI
from openai import AssistantEventHandler
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pytz
import os
import logging
from typing_extensions import override

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configura tu cliente con la API key desde el entorno
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ID del asistente
assistant_id = os.getenv("ASSISTANT_ID", "asst_Q3M9vDA4aN89qQNH1tDXhjaE")

# Diccionario para almacenar el thread_id de cada usuario
user_threads = {}

# Parámetros de Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = ('/etc/secrets/GOOGLE_SERVICE_ACCOUNT_FILE.json')  # Asegúrate de que esta ruta sea correcta
CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')

# Función para crear eventos en Google Calendar
def create_event(start_time, end_time, summary):
    try:
        # Verifica que las credenciales y la conexión estén funcionando
        credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('calendar', 'v3', credentials=credentials)

        # Verificar que las credenciales estén funcionando correctamente
        if service:
            logger.info("Conexión exitosa con Google Calendar.")
        else:
            logger.error("Error en la conexión con Google Calendar.")
            return None

        event = {
            'summary': summary,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'America/New_York',  # Asegúrate de usar el timezone correcto
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'America/New_York',
            },
        }

        # Crear el evento en Google Calendar
        event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        logger.info(f'Evento creado: {event.get("htmlLink")}')
        return event
    except Exception as e:
        logger.error(f"Error al crear el evento: {str(e)}")
        return None

# Función para procesar el mensaje del asistente y crear el evento
def create_event_from_assistant_response(message):
    try:
        # Aquí asumimos que el mensaje del asistente tiene el formato adecuado
        # Ejemplo de formato esperado del asistente:
        # - summary: Cita Prueba
        # - start: 2024-12-30T14:00:00+00:00
        # - end: 2024-12-30T15:00:00+00:00

        # Buscar las fechas y la hora del mensaje del asistente
        start_datetime_str = "2024-12-30T14:00:00+00:00"  # Ejemplo de cómo puede ser proporcionado
        end_datetime_str = "2024-12-30T15:00:00+00:00"

        # Convertir las cadenas ISO 8601 a objetos datetime
        start_datetime = datetime.fromisoformat(start_datetime_str)
        end_datetime = datetime.fromisoformat(end_datetime_str)

        # Convertir a la zona horaria de tu preferencia, por ejemplo "America/New_York"
        start_datetime = start_datetime.astimezone(pytz.timezone("America/New_York"))
        end_datetime = end_datetime.astimezone(pytz.timezone("America/New_York"))

        # Llamar a la función que crea el evento en Google Calendar
        create_event(start_datetime, end_datetime, "Cita Prueba")

    except Exception as e:
        logger.error(f"Error al procesar el evento: {e}")

# Crear un manejador de eventos para manejar el stream de respuestas del asistente
class EventHandler(AssistantEventHandler):
    def __init__(self):
        super().__init__()
        self.assistant_message = ""

    @override
    def on_text_created(self, text) -> None:
        logger.info(f"Asistente: {text.value}")  # Cambié esto para no usar 'end'
        self.assistant_message += text.value

    @override
    def on_text_delta(self, delta, snapshot):
        logger.info(delta.value)  # Cambié esto para no usar 'end'
        self.assistant_message += delta.value

@app.route('/generate-response', methods=['POST'])
def generate_response():
    data = request.json
    user_message = data.get('message')
    user_id = data.get('sender_id')

    if not user_message or not user_id:
        logger.error("No se proporcionó un mensaje o ID de usuario válido.")
        return jsonify({'response': "No se proporcionó un mensaje o ID de usuario válido."}), 400

    logger.info(f"Mensaje recibido del usuario {user_id}: {user_message}")

    try:
        if user_id not in user_threads:
            thread = client.beta.threads.create()
            logger.info(f"Hilo creado para el usuario {user_id}: {thread.id}")
            user_threads[user_id] = thread.id
        else:
            thread_id = user_threads[user_id]

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

        assistant_message = event_handler.assistant_message
        logger.info(f"Mensaje generado por el asistente: {assistant_message}")

        # Verificar si el mensaje contiene información para crear un evento
        if "evento" in assistant_message.lower():
            create_event_from_assistant_response(assistant_message)

    except Exception as e:
        logger.error(f"Error al generar respuesta: {str(e)}")
        return jsonify({'response': f"Error al generar respuesta: {str(e)}"}), 500

    return jsonify({'response': assistant_message})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
