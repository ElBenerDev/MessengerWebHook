import requests
from datetime import datetime
import pytz

# Datos de autenticación
PIPEDRIVE_API_KEY = '8f2492eead4201ac69582ee4f3dfefd13d818b79'
COMPANY_DOMAIN = 'companiademuestra'

# Definición del horario laboral (en formato 24 horas)
WORKING_HOURS_START = "09:00"
WORKING_HOURS_END = "18:00"

# Zona horaria de Argentina
ARGENTINA_TZ = pytz.timezone("America/Argentina/Buenos_Aires")

# Función para convertir horario de Argentina a UTC
def convert_to_utc(date_str, time_str):
    local_time = ARGENTINA_TZ.localize(datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M"))
    utc_time = local_time.astimezone(pytz.utc)
    return utc_time.strftime("%H:%M")  # Devuelve solo la hora en formato UTC

# Función para validar si el horario está dentro del horario laboral
def is_within_working_hours(activity_due_time):
    return WORKING_HOURS_START <= activity_due_time <= WORKING_HOURS_END

# Función para verificar actividades existentes
def check_existing_appointments(due_date, due_time):
    activity_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/activities?api_token={PIPEDRIVE_API_KEY}'
    activities = []
    
    try:
        while activity_url:
            response = requests.get(activity_url)
            if response.status_code == 200:
                data = response.json()
                if data and 'data' in data:
                    activities.extend(data['data'])
                    activity_url = data.get('additional_data', {}).get('next_page', None)
                else:
                    break
            else:
                print(f"Error al obtener las actividades: {response.status_code}")
                print(response.text)
                break
    except Exception as e:
        print(f"Ocurrió un error al obtener actividades: {e}")
    
    for activity in activities:
        if activity.get('due_date') == due_date and activity.get('due_time') == due_time:
            return True
    return False

# Flujo principal
if __name__ == "__main__":
    contact_name = input("Ingrese el nombre del paciente: ")
    contact_phone = input("Ingrese el teléfono del paciente: ")
    contact_email = input("Ingrese el correo electrónico del paciente: ")

    # Ingreso de fecha y hora con validación
    while True:
        activity_due_date = f"2025-" + input("Ingrese el mes y día de la cita (MM-DD): ")
        try:
            datetime.strptime(activity_due_date, "%Y-%m-%d")
            break
        except ValueError:
            print("Fecha inválida. Intente nuevamente.")

    while True:
        activity_due_time = input("Ingrese la hora de la cita (HH:MM, entre 09:00 y 18:00): ")
        try:
            datetime.strptime(activity_due_time, "%H:%M")
            if is_within_working_hours(activity_due_time):
                break
            else:
                print("Hora fuera del horario laboral. Intente nuevamente.")
        except ValueError:
            print("Hora inválida. Intente nuevamente.")

    # Convertir a UTC
    utc_due_time = convert_to_utc(activity_due_date, activity_due_time)

    if check_existing_appointments(activity_due_date, utc_due_time):
        print("La cita no se puede crear porque ya hay una actividad programada en ese horario.")
    else:
        print("Cita dental creada exitosamente!")
