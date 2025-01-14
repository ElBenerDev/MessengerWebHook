from datetime import datetime
import pytz  # Asegúrate de instalar esta biblioteca: pip install pytz
import requests

# Datos de autenticación
PIPEDRIVE_API_KEY = '8f2492eead4201ac69582ee4f3dfefd13d818b79'
COMPANY_DOMAIN = 'companiademuestra'

# Zona horaria de Argentina
ARGENTINA_TZ = pytz.timezone('America/Argentina/Buenos_Aires')

# Año fijo
FIXED_YEAR = 2025


# Función para convertir horario de Argentina a UTC
def convert_to_utc(date_str, time_str):
    local_time = ARGENTINA_TZ.localize(datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M"))
    utc_time = local_time.astimezone(pytz.utc)
    return utc_time.strftime("%H:%M")  # Devuelve solo la hora en formato UTC


# Obtener el ID del propietario dinámicamente desde la API
def get_owner_id():
    url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/users?api_token={PIPEDRIVE_API_KEY}'
    response = requests.get(url)
    if response.status_code == 200:
        users_data = response.json().get('data', [])
        for user in users_data:
            if user.get('active_flag') == 1:  # Usuario activo
                return user['id']
    print(f"Error al obtener el ID del propietario: {response.status_code}")
    print(response.text)
    return None


# Función para crear contacto
def create_patient_contact(contact_name, phone=None, email=None):
    contact_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/persons?api_token={PIPEDRIVE_API_KEY}'
    contact_data = {
        'name': contact_name,
        'phone': phone,
        'email': email,
    }

    response = requests.post(contact_url, json=contact_data)
    if response.status_code == 201:
        return response.json().get('data', {}).get('id')
    print(f"Error al crear el contacto: {response.status_code}")
    print(response.text)
    return None


# Función para crear lead
def create_patient_lead(contact_id, lead_title, lead_owner_id):
    lead_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/leads?api_token={PIPEDRIVE_API_KEY}'
    lead_data = {
        'title': lead_title,
        'person_id': contact_id,
        'owner_id': lead_owner_id,
    }

    response = requests.post(lead_url, json=lead_data)
    if response.status_code == 201:
        return response.json().get('data', {}).get('id')
    print(f"Error al crear el lead: {response.status_code}")
    print(response.text)
    return None


# Verificar si ya existe una actividad para la misma fecha y hora
def check_existing_appointments(activity_due_date, activity_due_time):
    activity_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/activities?api_token={PIPEDRIVE_API_KEY}'

    response = requests.get(activity_url)
    if response.status_code == 200:
        activities = response.json().get('data', [])
        for activity in activities:
            if activity.get('due_date') == activity_due_date and activity.get('due_time') == activity_due_time:
                print(f"Ya existe una actividad: {activity['subject']} programada en este horario.")
                return True
        return False
    print(f"Error al consultar actividades: {response.status_code}")
    print(response.text)
    return False


# Crear cita dental
def create_dental_appointment(lead_id, activity_subject, activity_type, activity_due_date, activity_due_time, activity_duration, activity_note):
    activity_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/activities?api_token={PIPEDRIVE_API_KEY}'

    # Convertir horario a UTC
    utc_due_time = convert_to_utc(activity_due_date, activity_due_time)

    # Verificar si ya existe una actividad
    if not check_existing_appointments(activity_due_date, utc_due_time):
        activity_data = {
            'subject': activity_subject,
            'type': activity_type,
            'due_date': activity_due_date,
            'due_time': utc_due_time,
            'duration': activity_duration,
            'lead_id': lead_id,
            'note': activity_note,
        }

        response = requests.post(activity_url, json=activity_data)
        if response.status_code == 201:
            print("Cita dental creada exitosamente!")
        else:
            print(f"Error al crear la cita dental: {response.status_code}")
            print(response.text)
    else:
        print("No se puede crear la cita. Ya hay una actividad programada en este horario.")


# Flujo principal
if __name__ == "__main__":
    # Obtener el ID del propietario
    lead_owner_id = get_owner_id()
    if lead_owner_id:
        contact_name = input("Ingrese el nombre del paciente: ")
        contact_phone = input("Ingrese el teléfono del paciente: ")
        contact_email = input("Ingrese el correo electrónico del paciente: ")

        activity_due_date = f"{FIXED_YEAR}-" + input("Ingrese el mes y día de la cita (MM-DD): ")
        activity_due_time = input("Ingrese la hora de la cita (HH:MM): ")

        contact_id = create_patient_contact(contact_name, phone=contact_phone, email=contact_email)
        if contact_id:
            lead_title = f"Lead para {contact_name}"
            lead_id = create_patient_lead(contact_id, lead_title, lead_owner_id)
            if lead_id:
                create_dental_appointment(
                    lead_id,
                    f'Cita de Revisión dental para {contact_name}',
                    "meeting",
                    activity_due_date,
                    activity_due_time,
                    "00:30",
                    "Tipo de tratamiento: Revisión dental"
                )
