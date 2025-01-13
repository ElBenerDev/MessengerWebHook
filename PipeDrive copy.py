from datetime import datetime, timedelta
import pytz  # Asegúrate de instalar esta biblioteca: pip install pytz
import requests

# Datos de autenticación
PIPEDRIVE_API_KEY = '8f2492eead4201ac69582ee4f3dfefd13d818b79'
COMPANY_DOMAIN = 'companiademuestra'

# Zona horaria de Argentina
ARGENTINA_TZ = pytz.timezone('America/Argentina/Buenos_Aires')

# Variables para el Contacto (Persona)
contact_name = "Juan Pérez"
contact_phone = "+1234567890"
contact_email = "juan.perez@email.com"

# Variables para el Lead
lead_title = "Lead para Juan Pérez"
lead_owner_id = 23104380

# Variables para la Actividad (Cita Dental)
activity_subject = f'Cita de Revisión dental para {lead_title}'
activity_type = "meeting"   
activity_due_date = "2025-01-15"
activity_due_time = "07:00"  # Hora local en Argentina
activity_duration = "00:30"
activity_note = "Tipo de tratamiento: Revisión dental"

# Función para convertir horario de Argentina a UTC
def convert_to_utc(date_str, time_str):
    local_time = ARGENTINA_TZ.localize(datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M"))
    utc_time = local_time.astimezone(pytz.utc)
    return utc_time.strftime("%H:%M")  # Devuelve solo la hora en formato UTC


# Función para crear contacto
def create_patient_contact(contact_name, phone=None, email=None):
    contact_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/persons?api_token={PIPEDRIVE_API_KEY}'
    contact_data = {
        'name': contact_name,
    }
    if phone:
        contact_data['phone'] = phone
    if email:
        contact_data['email'] = email

    response = requests.post(contact_url, json=contact_data)
    if response.status_code == 201:
        contact = response.json()
        return contact['data']['id']
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
        lead = response.json()
        return lead['data']['id']
    else:
        print(f"Error al crear el lead: {response.status_code}")
        print(response.text)
    return None

# Función para crear cita dental (actividad)
def create_dental_appointment(lead_id, activity_subject, activity_type, activity_due_date, activity_due_time, activity_duration, activity_note):
    activity_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/activities?api_token={PIPEDRIVE_API_KEY}'

    # Convertimos el horario a UTC
    utc_due_time = convert_to_utc(activity_due_date, activity_due_time)

    # Verificamos si ya existe una actividad para el día y hora
    if not check_existing_appointments(activity_due_date, utc_due_time):
        activity_data = {
            'subject': activity_subject,
            'type': activity_type,
            'due_date': activity_due_date,
            'due_time': utc_due_time,  # Enviamos el horario en UTC
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


# Función para verificar si ya existe una cita en el mismo horario
def check_existing_appointments(activity_due_date, activity_due_time):
    activity_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/activities?api_token={PIPEDRIVE_API_KEY}'

    response = requests.get(activity_url)
    if response.status_code == 200:
        activities = response.json().get('data', [])
        
        for activity in activities:
            # Verificamos si la actividad coincide en fecha y hora
            if activity['due_date'] == activity_due_date and activity['due_time'] == activity_due_time:
                print(f"Ya existe una actividad: {activity['subject']} programada en esta fecha y hora.")
                return True
        return False
    else:
        print(f"Error al consultar actividades: {response.status_code}")
        print(response.text)
    return False


# Flujo principal
if __name__ == "__main__":
    # Paso 1: Crear un contacto para el paciente
    contact_id = create_patient_contact(contact_name, phone=contact_phone, email=contact_email)

    # Paso 2: Crear el lead para el paciente
    if contact_id:
        lead_id = create_patient_lead(contact_id, lead_title, lead_owner_id)

        # Paso 3: Crear la cita dental para el paciente
        if lead_id:
            create_dental_appointment(lead_id, activity_subject, activity_type, activity_due_date, activity_due_time, activity_duration, activity_note)
