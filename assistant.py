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
import requests
import json
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

# Access Token de Mercado Pago (sandbox)
access_token = 'APP_USR-5019818987249464-123000-1bb2908a2fd9a65dfaa42a8ad2c38b3a-2183981747'
url = "https://api.mercadopago.com/checkout/preferences"

# Funciones auxiliares para Google Calendar
def build_service():
    """Crea y devuelve un servicio de Google Calendar."""
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('calendar', 'v3', credentials=credentials)

def create_payment_preference(amount):
    """Crea una preferencia de pago en Mercado Pago."""
    preference_data = {
        "items": [
            {
                "title": "Cita en el Calendario",
                "quantity": 1,
                "currency_id": "ARS",
                "unit_price": amount
            }
        ],
        "back_urls": {
            "success": "https://www.tusitio.com/success",
            "failure": "https://www.tusitio.com/failure",
            "pending": "https://www.tusitio.com/pending"
        },
        "auto_return": "approved"
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Realizamos la solicitud POST para crear la preferencia
    response = requests.post(url, data=json.dumps(preference_data), headers=headers)

    if response.status_code == 201:
        preference = response.json()
        return preference["init_point"]  # Retornamos el link para redirigir al usuario
    else:
        logger.error("Error al crear la preferencia de pago:", response.json())
        return None

def create_event(start_time, end_time, summary, amount):
    """Crea un evento en Google Calendar y genera una preferencia de pago en Mercado Pago."""
    try:
        service = build_service()

        event = {
            'summary': summary,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'America/Argentina/Buenos_Aires',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'America/Argentina/Buenos_Aires',
            },
        }

        # Crear el evento en Google Calendar
        event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        logger.info(f'Evento creado: {event.get("htmlLink")}')

        # Crear la preferencia de pago en Mercado Pago
        payment_url = create_payment_preference(amount)
        
        if payment_url:
            # Devuelves el link de pago junto con la URL del evento
            return {"event_url": event.get("htmlLink"), "payment_url": payment_url}
        else:
            return {"event_url": event.get("htmlLink"), "payment_url": None}

    except Exception as e:
        logger.error(f"Error al crear el evento: {e}")
        return None

def delete_event(event_summary):
    """Cancela un evento en Google Calendar."""
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

# Función para convertir fechas a la zona horaria local
def convert_to_local_timezone(datetime_obj):
    """Convierte la fecha y hora a la zona horaria local (Buenos Aires)"""
    local_tz = pytz.timezone('America/Argentina/Buenos_Aires')
    if datetime_obj.tzinfo is None:
        datetime_obj = local_tz.localize(datetime_obj)  # Si es naive, localizamos
    else:
        datetime_obj = datetime_obj.astimezone(local_tz)  # Si ya tiene zona horaria, la convertimos
    return datetime_obj

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

    @override
    def on_text_created(self, text) -> None:
        self.assistant_message += text.value

    @override
    def on_text_delta(self, delta, snapshot):
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

        if "start" in assistant_message.lower() and "end" in assistant_message.lower():
            start_datetime_str, end_datetime_str = extract_datetime_from_message(assistant_message)

            if start_datetime_str and end_datetime_str:
                start_datetime = datetime.fromisoformat(start_datetime_str)
                end_datetime = datetime.fromisoformat(end_datetime_str)

                # Convertir las fechas a la zona horaria correcta
                start_datetime = convert_to_local_timezone(start_datetime)
                end_datetime = convert_to_local_timezone(end_datetime)

                # Llamar a la función para crear el evento y obtener la URL del pago
                payment_amount = 100.00  # Ejemplo: el costo de la cita es 100
                result = create_event(start_datetime, end_datetime, "Cita prueba", payment_amount)

                if result:
                    event_url = result.get("event_url")
                    payment_url = result.get("payment_url")
                    if payment_url:
                        return jsonify({
                            'response': f'El evento fue creado exitosamente: {event_url}. Para completar el pago, por favor visita: {payment_url}'
                        })
                    else:
                        return jsonify({
                            'response': f'El evento fue creado exitosamente: {event_url}.'
                        })

        elif "cancelar" in user_message.lower():
            summary_match = re.search(r'cita\s+(.*)', user_message.lower())
            if summary_match:
                summary = summary_match.group(1).strip()
                response_message = delete_event(summary)
                return jsonify({'response': response_message})

    except Exception as e:
        logger.error(f"Error al generar respuesta: {e}")
        return jsonify({'response': f"Error al generar respuesta: {e}"}), 500

    return jsonify({'response': assistant_message})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
