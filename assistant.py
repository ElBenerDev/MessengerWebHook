from flask import Flask, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pytz
import os
import logging
from openai import OpenAI
from openai import AssistantEventHandler
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

# Configuración de Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')

# Helper para autenticar Google Calendar
def authenticate_google_calendar():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build('calendar', 'v3', credentials=credentials)

# Crear evento en Google Calendar
def create_event(start_time, end_time, summary):
    service = authenticate_google_calendar()
    event = {
        'summary': summary,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'America/New_York',
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'America/New_York',
        },
    }
    created_event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
    logger.info(f"Evento creado: {created_event.get('htmlLink')}")
    return created_event.get('htmlLink')

# Crear un manejador de eventos para manejar el stream de respuestas del asistente
class EventHandler(AssistantEventHandler):
    def __init__(self):
        super().__init__()
        self.assistant_message = ""

    @override
    def on_text_created(self, text) -> None:
        print(f"Asistente: {text.value}", end="", flush=True)
        self.assistant_message += text.value

    @override
    def on_text_delta(self, delta, snapshot):
        print(delta.value, end="", flush=True)
        self.assistant_message += delta.value

# Endpoint para crear eventos desde un mensaje
@app.route('/create-event', methods=['POST'])
def create_event_endpoint():
    data = request.json
    prompt = data.get('message')
    user_id = data.get('sender_id')

    if not prompt or not user_id:
        return jsonify({'error': 'Faltan parámetros requeridos.'}), 400

    try:
        # Usar el modelo de OpenAI para extraer eventos desde el mensaje
        logger.info(f"Mensaje recibido del usuario {user_id}: {prompt}")
        
        # Crear un hilo de conversación para el usuario si no existe
        if user_id not in user_threads:
            thread = client.beta.threads.create()
            logger.info(f"Hilo creado para el usuario {user_id}: {thread.id}")
            user_threads[user_id] = thread.id

        # Enviar el mensaje del usuario al hilo existente
        client.beta.threads.messages.create(
            thread_id=user_threads[user_id],
            role="user",
            content=prompt
        )

        # Crear y manejar la respuesta del asistente
        event_handler = EventHandler()
        with client.beta.threads.runs.stream(
            thread_id=user_threads[user_id],
            assistant_id=assistant_id,
            event_handler=event_handler,
        ) as stream:
            stream.until_done()

        # Obtener el mensaje generado por el asistente
        assistant_message = event_handler.assistant_message
        logger.info(f"Mensaje generado por el asistente: {assistant_message}")

        # Extraer eventos del mensaje generado por el asistente
        events = assistant_message.strip().split(';')

        start_time = datetime.now(pytz.timezone('America/New_York'))
        event_links = []

        for i, summary in enumerate(events):
            end_time = start_time + timedelta(hours=1)
            event_link = create_event(start_time, end_time, summary.strip())
            event_links.append(event_link)
            start_time += timedelta(days=1)  # Asumimos eventos consecutivos por días

        return jsonify({'status': 'success', 'event_links': event_links})

    except Exception as e:
        logger.error(f"Error al crear eventos: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Endpoint para generar respuestas del asistente
@app.route('/generate-response', methods=['POST'])
def generate_response():
    data = request.json
    user_message = data.get('message')
    user_id = data.get('sender_id')

    if not user_message or not user_id:
        return jsonify({'response': "No se proporcionó un mensaje o ID de usuario válido."}), 400

    logger.info(f"Mensaje recibido del usuario {user_id}: {user_message}")

    try:
        # Verificar si ya existe un thread_id para este usuario
        if user_id not in user_threads:
            # Crear un nuevo hilo de conversación si no existe
            thread = client.beta.threads.create()
            logger.info(f"Hilo creado para el usuario {user_id}: {thread.id}")
            user_threads[user_id] = thread.id
        else:
            thread_id = user_threads[user_id]

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

        # Obtener el mensaje generado por el asistente
        assistant_message = event_handler.assistant_message
        logger.info(f"Mensaje generado por el asistente: {assistant_message}")

        # Verificar si el asistente ha confirmado que creará la cita
        if "Voy a proceder a crearla" in assistant_message:
            # Extraer los detalles del evento desde el mensaje del asistente
            # Suponemos que el asistente devuelve la información de la cita correctamente
            # Por ejemplo, extraeremos el título y la hora de la cita
            event_details = {
                "title": "Cita de prueba",  # Puede ser extraído del mensaje si se especifica
                "start_time": datetime(2024, 12, 5, 16, 0),  # Hora de inicio
                "duration": timedelta(hours=2),  # Duración de 2 horas
                "reminder": None,  # Sin recordatorio
            }

            # Crear el evento en Google Calendar
            event_link = create_event(event_details["start_time"], 
                                      event_details["start_time"] + event_details["duration"], 
                                      event_details["title"])

            # Devolver la respuesta al usuario
            return jsonify({'response': f"Evento creado con éxito. Enlace al evento: {event_link}"}), 200

    except Exception as e:
        logger.error(f"Error al generar respuesta: {str(e)}")
        return jsonify({'response': f"Error al generar respuesta: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
