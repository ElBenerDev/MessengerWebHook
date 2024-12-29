from flask import Flask, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pytz
import os
import logging
import openai

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuración de Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = './asistenteCalendarioCredentials.json'
CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')

# Configuración de OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Diccionario para almacenar eventos por usuario
user_events = {}

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
        response = openai.Completion.create(
            engine="davinci",
            prompt=f"Extrae eventos del siguiente texto:\n{prompt}\nDevuelve una lista de eventos separados por punto y coma:",
            max_tokens=150,
            temperature=0.5,
        )
        events = response.choices[0].text.strip().split(';')

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

# Endpoint para generar respuestas (interacción del asistente)
@app.route('/generate-response', methods=['POST'])
def generate_response():
    data = request.json
    user_message = data.get('message')
    user_id = data.get('sender_id')

    if not user_message or not user_id:
        return jsonify({'error': 'Faltan parámetros requeridos.'}), 400

    logger.info(f"Mensaje recibido del usuario {user_id}: {user_message}")

    try:
        # Usar el modelo de OpenAI para generar la respuesta
        response = openai.Completion.create(
            engine="davinci",
            prompt=f"Responde al siguiente mensaje:\n{user_message}",
            max_tokens=150,
            temperature=0.5,
        )
        response_message = response.choices[0].text.strip()
        logger.info(f"Respuesta generada: {response_message}")
        return jsonify({'response': response_message})

    except Exception as e:
        logger.error(f"Error al generar respuesta: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
