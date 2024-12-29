# main.py
from flask import Flask, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import openai
import pytz
import os
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables desde .env
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID")

# Configuración de API Keys
openai.api_key = OPENAI_API_KEY

SCOPES = ['https://www.googleapis.com/auth/calendar']

def create_event(start_time, end_time, summary):
    """Crea un evento en Google Calendar."""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        service = build('calendar', 'v3', credentials=credentials)

        event = {
            'summary': summary,
            'start': {'dateTime': start_time.isoformat(), 'timeZone': 'America/New_York'},
            'end': {'dateTime': end_time.isoformat(), 'timeZone': 'America/New_York'},
        }

        created_event = service.events().insert(calendarId=GOOGLE_CALENDAR_ID, body=event).execute()
        logger.info(f"Evento creado: {created_event['htmlLink']}")
        return created_event['htmlLink']

    except Exception as e:
        logger.error(f"Error al crear evento: {e}", exc_info=True)
        raise

def generate_openai_response(prompt):
    """Genera una respuesta usando OpenAI."""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente útil."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        return response['choices'][0]['message']['content']

    except Exception as e:
        logger.error(f"Error al interactuar con OpenAI: {e}", exc_info=True)
        raise

# Configuración de Flask
app = Flask(__name__)

@app.route('/generate-response', methods=['POST'])
def generate_response():
    try:
        data = request.json
        prompt = data.get('message', '')

        if not prompt:
            return jsonify({'error': 'No se proporcionó el mensaje en el cuerpo de la solicitud.'}), 400

        logger.info(f"Mensaje recibido: {prompt}")

        # Generar respuesta con OpenAI
        openai_response = generate_openai_response(prompt)
        logger.info(f"Respuesta de OpenAI: {openai_response}")

        # Crear eventos en Google Calendar (si aplica)
        events = openai_response.split('\n')
        start_time = datetime.now(pytz.timezone('America/New_York'))

        created_events = []
        for summary in events:
            if summary.strip():
                end_time = start_time + timedelta(hours=1)
                event_link = create_event(start_time, end_time, summary.strip())
                created_events.append({'summary': summary.strip(), 'link': event_link})
                start_time += timedelta(days=1)

        return jsonify({'response': openai_response, 'created_events': created_events})

    except Exception as e:
        logger.error(f"Error al procesar la solicitud: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
