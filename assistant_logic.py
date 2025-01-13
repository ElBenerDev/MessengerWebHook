import requests
import logging
import os
from datetime import datetime
import pytz

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Función para convertir hora local a UTC
def convert_to_utc(local_datetime_str, local_tz_str='America/Argentina/Buenos_Aires'):
    try:
        # Convertir la fecha y hora local a un objeto datetime
        local_tz = pytz.timezone(local_tz_str)
        local_datetime = datetime.strptime(local_datetime_str, '%Y-%m-%d %H:%M')
        local_datetime = local_tz.localize(local_datetime)  # Añadir información de la zona horaria local
        utc_datetime = local_datetime.astimezone(pytz.utc)  # Convertir a UTC
        return utc_datetime.strftime('%H:%M')  # Solo retorna la hora en UTC
    except Exception as e:
        logger.error(f"Error al convertir a UTC: {e}")
        return None

# Función para crear una actividad en Pipedrive
def create_activity(subject, due_date, lead_id):
    PIPEDRIVE_API_KEY = '8f2492eead4201ac69582ee4f3dfefd13d818b79'
    COMPANY_DOMAIN = 'companiademuestra'
    
    # Forzar la hora a las 5:00 PM (hora local de Argentina)
    forced_due_time = "17:00"
    local_datetime_str = f"{due_date} {forced_due_time}"
    
    # Convertir la hora local a UTC
    activity_due_time_utc = convert_to_utc(local_datetime_str, local_tz_str='America/Argentina/Buenos_Aires')
    
    if not activity_due_time_utc:
        logger.error("No se pudo convertir la hora local a UTC. Verifica la fecha y hora proporcionadas.")
        return

    # Crear los datos de la actividad
    activity_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/activities?api_token={PIPEDRIVE_API_KEY}'
    activity_data = {
        'subject': subject,
        'type': 'meeting',
        'due_date': due_date,  # Fecha de la actividad
        'due_time': activity_due_time_utc,  # Hora UTC correcta
        'duration': '01:00',  # Duración de 1 hora
        'lead_id': lead_id
    }
    
    logger.info(f"Datos enviados a Pipedrive: {activity_data}")

    # Hacer la solicitud POST a la API de Pipedrive
    try:
        response = requests.post(activity_url, json=activity_data)
        if response.status_code == 201:
            logger.info("Actividad creada exitosamente!")
        else:
            logger.error(f"Error al crear la actividad: {response.status_code}")
            logger.error(response.text)
    except Exception as e:
        logger.error(f"Error en la solicitud a Pipedrive: {e}")

# Prueba de la función
if __name__ == "__main__":
    subject = "Reunión inicial con cliente"
    due_date = "2025-01-13"  # Fecha correcta
    lead_id = 123456  # ID ficticio del lead para pruebas

    create_activity(subject, due_date, lead_id)
