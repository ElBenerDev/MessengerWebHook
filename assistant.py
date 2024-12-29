from flask import Flask, request, jsonify
from openai import OpenAI
from openai import AssistantEventHandler
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pytz
import os
import logging
import re

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
SERVICE_ACCOUNT_FILE = os.getenv('/etc/secrets/GOOGLE_SERVICE_ACCOUNT_FILE.json')
CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')

# Función para crear eventos en Google Calendar
def create_event(start_time, end_time, summary):
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=credentials)
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
    event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
    logger.info('Evento creado: %s' % (event.get('htmlLink')))

# Crear un manejador de eventos para manejar el stream de respuestas del asistente
class EventHandler(AssistantEventHandler):
    def __init__(self):
        super().__init__()
        self.assistant_message = ""

    def on_text_created(self, text) -> None:
        print(f"Asistente: {text.value}", end="", flush=True)
        self.assistant_message += text.value

    def on_text_delta(self, delta, snapshot):
        print(delta.value, end="", flush=True)
        self.assistant_message += delta.value

# Función para extraer la fecha y hora del mensaje
def extract_datetime(message):
    # Usaremos expresiones regulares para extraer la fecha y la hora del mensaje
    date_pattern = r"\b(\d{1,2})\s*(de)?\s*(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s*(de)?\s*(\d{4})\b"
    time_pattern = r"\b(\d{1,2}):(\d{2})\b"
    
    date_match = re.search(date_pattern, message, re.IGNORECASE)
    time_match = re.search(time_pattern, message)

    if date_match and time_match:
        day = int(date_match.group(1))
        month = date_match.group(3).lower()
        year = int(date_match.group(5))
        hour = int(time_match.group(1))
        minute = int(time_match.group(2))

        # Mapear el nombre del mes al número correspondiente
        months = {
            "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5,
            "junio": 6, "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10,
            "noviembre": 11, "diciembre": 12
        }
        
        # Crear un objeto datetime con la fecha y hora extraída
        event_date = datetime(year, months[month], day, hour, minute, tzinfo=pytz.timezone('America/New_York'))
        return event_date
    return None

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

        # Verificar si el mensaje contiene información para crear un evento
        if "evento" in assistant_message.lower():
            # Extraer la fecha y hora del mensaje del asistente
            event_datetime = extract_datetime(assistant_message)
            if event_datetime:
                # Crear un evento basado en la respuesta del asistente
                start_time = event_datetime
                end_time = start_time + timedelta(hours=1)  # Duración de 1 hora para el evento

                # Crear el evento en Google Calendar
                create_event(start_time, end_time, assistant_message)
            else:
                logger.error("No se pudo extraer la fecha y hora del mensaje.")
                return jsonify({'response': "No pude encontrar una fecha y hora válidas para el evento."}), 400

    except Exception as e:
        logger.error(f"Error al generar respuesta: {str(e)}")
        return jsonify({'response': f"Error al generar respuesta: {str(e)}"}), 500

    return jsonify({'response': assistant_message})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
