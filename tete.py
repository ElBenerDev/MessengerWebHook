import os
import pickle
import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# Si modificas estos alcances, elimina el archivo token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar']

def authenticate_google_account():
    """Autenticación y autorización con Google OAuth 2.0"""
    creds = None
    # El archivo token.pickle almacena el token de acceso del usuario.
    # Si no existe, el usuario deberá iniciar sesión.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # Si no hay credenciales válidas disponibles, deja que el usuario inicie sesión.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Guarda las credenciales para la próxima ejecución.
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    # Llama al API de Google Calendar
    service = build('calendar', 'v3', credentials=creds)
    return service

def create_event(service, start_time, end_time, summary, description):
    """Crea un evento en Google Calendar"""
    event = {
        'summary': summary,
        'location': 'Lugar del evento',
        'description': description,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'America/Mexico_City',
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'America/Mexico_City',
        },
    }
    
    event_result = service.events().insert(
        calendarId='primary', body=event).execute()
    print(f"Evento creado: {event_result['htmlLink']}")

if __name__ == '__main__':
    # Autenticación
    service = authenticate_google_account()

    # Definir los detalles del evento
    start_time = datetime.datetime(2025, 1, 10, 14, 0)  # 10 de enero, 2025, 14:00
    end_time = start_time + datetime.timedelta(hours=1)
    summary = 'Proyecto'
    description = 'Descripción del proyecto'

    # Crear el evento
    create_event(service, start_time, end_time, summary, description)
