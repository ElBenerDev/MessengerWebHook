from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import os
import logging
import requests

# Parámetros de Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', '/etc/secrets/GOOGLE_SERVICE_ACCOUNT_FILE.json')
CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')

# Validar si la variable de entorno CALENDAR_ID está presente
if not CALENDAR_ID:
    raise EnvironmentError("La variable de entorno 'GOOGLE_CALENDAR_ID' no está configurada.")

def build_service():
    """Crea y devuelve un servicio de Google Calendar."""
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build('calendar', 'v3', credentials=credentials)

def create_event(start_time, end_time, summary, description=None, reminders=None):
    """Crea un evento en Google Calendar sin asistentes."""
    try:
        service = build_service()
        event = {
            'summary': summary,
            'description': description,
            'start': {'dateTime': start_time.isoformat(), 'timeZone': 'America/Argentina/Buenos_Aires'},
            'end': {'dateTime': end_time.isoformat(), 'timeZone': 'America/Argentina/Buenos_Aires'},
            'reminders': {'useDefault': False, 'overrides': reminders or []}
        }
        event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        logging.info(f"Evento creado: {event.get('htmlLink')}")
        return event
    except Exception as e:
        logging.error(f"Error al crear el evento: {e}")
        raise

def send_whatsapp_message(to, message):
    """Envía un mensaje de WhatsApp al usuario."""
    url = 'https://graph.facebook.com/v15.0/{your_phone_number_id}/messages'
    headers = {
        'Authorization': 'Bearer {your_access_token}',
        'Content-Type': 'application/json',
    }
    data = {
        'messaging_product': 'whatsapp',
        'to': to,
        'text': {
            'body': message
        }
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()

def handle_event_creation(user_message, user_phone):
    """Maneja la creación de un evento dependiendo de la respuesta del usuario."""
    if user_message.lower() == "correcto":
        # Aquí defines los datos del evento a crear
        start_time = datetime(2025, 1, 10, 14, 0)  # 10 de enero de 2025, 2:00 PM
        end_time = start_time + timedelta(hours=1)
        summary = 'Proyecto'
        description = 'Descripción del proyecto'
        reminders = [{'method': 'popup', 'minutes': 10}]  # Recordatorio 10 minutos antes

        # Crear el evento en Google Calendar sin asistentes
        try:
            event = create_event(start_time, end_time, summary, description, reminders)
            event_link = event.get('htmlLink')  # Obtener el link del evento creado

            # Enviar la confirmación por WhatsApp
            confirmation_message = f"¡Genial! El evento 'Proyecto' ha sido creado. Puedes verlo aquí: {event_link}"
            send_whatsapp_message(user_phone, confirmation_message)
            print(f"Evento creado: {event_link}")
        except Exception as e:
            send_whatsapp_message(user_phone, "Hubo un problema al procesar tu mensaje.")
            print(f"Error al crear el evento: {e}")
            return False
        return True
    else:
        # Si el mensaje no es "correcto", enviar un mensaje indicando que el evento no se ha creado
        send_whatsapp_message(user_phone, "No se ha creado el evento. Por favor confirma los detalles correctamente.")
        return False

def listen_whatsapp_messages():
    """Función para simular la escucha de los mensajes de WhatsApp."""
    while True:
        # Aquí va tu lógica real para recibir mensajes de WhatsApp
        user_message = input("Mensaje de usuario (escribe 'correcto' para confirmar el evento): ")
        user_phone = input("Número de teléfono del usuario: ")

        # Llama a la función de manejo de eventos cuando se recibe un mensaje
        if handle_event_creation(user_message, user_phone):
            print("Evento creado con éxito.")
        else:
            print("No se ha creado el evento.")

if __name__ == '__main__':
    listen_whatsapp_messages()
