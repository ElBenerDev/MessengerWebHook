from flask import Flask, request, jsonify
from openai import OpenAI
from openai import AssistantEventHandler
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime
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
SERVICE_ACCOUNT_FILE = '/etc/secrets/GOOGLE_SERVICE_ACCOUNT_FILE.json'  # Asegúrate de que esta ruta sea correcta
CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')

# Funciones auxiliares para Google Calendar
def build_service():
    """Crea y devuelve un servicio de Google Calendar."""
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('calendar', 'v3', credentials=credentials)

def create_event(start_time, end_time, summary, description=None):
    try:
        service = build_service()

        event = {
            'summary': summary,  # Título: Nombre del cliente
            'description': description,  # Descripción: Contexto del asistente
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'America/Argentina/Buenos_Aires',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'America/Argentina/Buenos_Aires',
            },
        }

        event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        logger.info(f'Evento creado: {event.get("htmlLink")}')
        return event
    except Exception as e:
        logger.error(f"Error al crear el evento: {e}")
        return None

def delete_event(event_summary):
    try:
        service = build_service()

        # Listar eventos para encontrar el que coincida
        now = datetime.utcnow().isoformat() + 'Z'  # Hora actual en formato RFC3339
        events_result = service.events().list(calendarId=CALENDAR_ID, timeMin=now, singleEvents=True, orderBy='startTime').execute()
        events = events_result.get('items', [])

        logger.info(f"{len(events)} eventos encontrados para analizar.")

        for event in events:
            logger.debug(f"Analizando evento: {event['summary']} con ID {event['id']}")
            if event_summary.lower() in event['summary'].lower():
                service.events().delete(calendarId=CALENDAR_ID, eventId=event['id']).execute()
                logger.info(f"Evento eliminado: {event['summary']}")
                return f"El evento '{event['summary']}' ha sido cancelado con éxito."

        logger.warning(f"No se encontró el evento con el resumen: {event_summary}")
        return f"No se encontró el evento '{event_summary}'."
    except Exception as e:
        logger.error(f"Error al eliminar el evento: {e}")
        return f"Hubo un error al intentar cancelar el evento: {e}"

# Procesamiento del asistente
def extract_datetime_from_message(message):
    try:
        start_match = re.search(r'\*\*start\*\*:\s*([\d\-T:+]+)', message)
        end_match = re.search(r'\*\*end\*\*:\s*([\d\-T:+]+)', message)

        if start_match and end_match:
            start_datetime_str = start_match.group(1)
            end_datetime_str = end_match.group(1)
            logger.info(f"Fechas extraídas - Inicio: {start_datetime_str}, Fin: {end_datetime_str}")
            return start_datetime_str, end_datetime_str
        else:
            logger.error("No se encontraron fechas válidas en el mensaje del asistente.")
            return None, None
    except Exception as e:
        logger.error(f"Error al extraer fechas del mensaje: {e}")
        return None, None

# Crear un manejador de eventos para manejar el stream de respuestas del asistente
class EventHandler(AssistantEventHandler):
    def __init__(self):
        super().__init__()
        self.assistant_message = ""
        self.message_complete = False

    @override
    def on_text_created(self, text) -> None:
        if not self.message_complete:
            # Evitar cualquier acumulación redundante
            if text.value not in self.assistant_message:
                self.assistant_message += text.value

    @override
    def on_text_delta(self, delta, snapshot):
        if not self.message_complete:
            # Solo agregar nuevo texto
            if delta.value not in self.assistant_message:
                self.assistant_message += delta.value

    def finalize_message(self):
        if not self.message_complete:
            # Marcar mensaje como completo evita más cambios
            self.message_complete = True
        return self.assistant_message.strip()  # Elimina cualquier espacio adicional o duplicación potencial


@app.route('/generate-response', methods=['POST'])
def generate_response():
    data = request.json
    user_message = data.get('message')
    user_id = data.get('sender_id')
    user_name = data.get('user_name', "Usuario")  # Nombre del cliente

    if not user_message or not user_id:
        logger.error("No se proporcionó un mensaje o ID de usuario válido.")
        return jsonify({'response': "No se proporcionó un mensaje o ID de usuario válido."}), 400

    logger.info(f"Mensaje recibido del usuario {user_id}: {user_message}")

    try:
        # Crear un nuevo thread para cada usuario si no existe
        if user_id not in user_threads:
            thread = client.beta.threads.create()
            user_threads[user_id] = thread.id
        thread_id = user_threads[user_id]

        # Crear y manejar la respuesta del asistente
        event_handler = EventHandler()
        with client.beta.threads.runs.stream(
            thread_id=thread_id,
            assistant_id=assistant_id,
            event_handler=event_handler,
        ) as stream:
            stream.until_done()

        assistant_message = event_handler.finalize_message()
        logger.info(f"Mensaje generado por el asistente: {assistant_message}")

    except Exception as e:
        logger.error(f"Error al generar respuesta: {e}")
        return jsonify({'response': f"Error al generar respuesta: {e}"}), 500

    return jsonify({'response': assistant_message})


# Ruta para la verificación del webhook de Facebook
@app.route('/webhook', methods=['GET'])
def webhook_verification():
    # Parámetros que Facebook enviará
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    # Verificar el token
    if mode == 'subscribe' and token == '12345':  # Cambia '12345' por tu token de verificación
        logger.info("Verificación exitosa del webhook.")
        return challenge  # Responder con el valor del challenge
    else:
        logger.error("Verificación fallida del webhook.")
        return "Error, invalid token", 403

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
