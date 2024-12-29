from flask import Flask, request, jsonify
import openai
from datetime import datetime, timedelta
import pytz
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de Flask
app = Flask(__name__)

# Cargar claves desde .env
openai.api_key = os.getenv('OPENAI_API_KEY')
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')

# Configuración de Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']

def create_event(start_time, end_time, summary):
    """Crea un evento en Google Calendar."""
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
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
    return event.get('htmlLink')

@app.route('/generate-response', methods=['POST'])
def generate_response():
    """Genera respuestas basadas en el mensaje del usuario y gestiona la creación de eventos."""
    data = request.json
    user_message = data.get('message')
    user_id = data.get('sender_id')

    if not user_message or not user_id:
        return jsonify({'response': "No se proporcionó un mensaje o ID de usuario válido."}), 400

    try:
        # Generar respuesta con ChatGPT
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente que ayuda a programar eventos en el calendario."},
                {"role": "user", "content": user_message}
            ],
            max_tokens=300,
            temperature=0.7,
        )

        assistant_message = response['choices'][0]['message']['content']

        # Lógica para crear eventos (si es relevante)
        if "crear evento" in user_message.lower():
            start_time = datetime.now(pytz.timezone('America/New_York'))
            end_time = start_time + timedelta(hours=1)
            event_link = create_event(start_time, end_time, assistant_message)

            return jsonify({'response': f"Evento creado: {event_link}"}), 200

        return jsonify({'response': assistant_message}), 200

    except Exception as e:
        return jsonify({'response': f"Error al procesar la solicitud: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
