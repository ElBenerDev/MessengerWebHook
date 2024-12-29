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

# Función para extraer fecha y hora del mensaje del usuario
def extract_datetime(message):
    # Expresión regular para detectar la fecha y hora
    date_pattern = r"(\d{1,2})\s*(de)?\s*(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s*(de)?\s*(\d{4})"
    time_pattern = r"(\d{1,2})(?:[:.])?(\d{2})?\s*(AM|PM|am|pm)?"

    # Buscar la fecha
    date_match = re.search(date_pattern, message, re.IGNORECASE)
    # Buscar la hora
    time_match = re.search(time_pattern, message, re.IGNORECASE)

    if date_match and time_match:
        day = int(date_match.group(1))
        month_name = date_match.group(3).lower()
        year = int(date_match.group(5))
        hour = int(time_match.group(1))
        minute = int(time_match.group(2) if time_match.group(2) else 0)

        # Mapear el nombre del mes al número correspondiente
        months = {
            "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5,
            "junio": 6, "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10,
            "noviembre": 11, "diciembre": 12
        }

        # Convertir la hora a 24 horas si es AM/PM
        if time_match.group(3):
            if time_match.group(3).lower() == "pm" and hour != 12:
                hour += 12
            elif time_match.group(3).lower() == "am" and hour == 12:
                hour = 0

        # Crear un objeto datetime con la fecha y hora extraída
        event_date = datetime(year, months[month_name], day, hour, minute, tzinfo=pytz.timezone('America/New_York'))
        return event_date
    else:
        logger.error(f"Mensaje recibido: {message}")
        logger.error("No se pudo extraer la fecha y hora con las expresiones regulares.")
        return None

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
            event_datetime = extract_datetime(assistant_message)
            if event_datetime:
                logger.info(f"Creando evento para la fecha y hora extraída: {event_datetime}")
                # Crear evento en Google Calendar
                create_event(event_datetime, event_datetime + timedelta(hours=1), "Cita Prueba")
            else:
                logger.error("No se pudo extraer la fecha y hora del mensaje del asistente.")
                return jsonify({'response': "No se pudo procesar la fecha y hora del evento."}), 400

    except Exception as e:
        logger.error(f"Error al generar respuesta: {str(e)}")
        return jsonify({'response': f"Error al generar respuesta: {str(e)}"}), 500

    return jsonify({'response': assistant_message})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
