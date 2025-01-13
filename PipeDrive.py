import requests
from datetime import datetime
import pytz

# Datos de autenticación
PIPEDRIVE_API_KEY = '8f2492eead4201ac69582ee4f3dfefd13d818b79'
COMPANY_DOMAIN = 'companiademuestra'

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
activity_due_time = "07:00"  # Hora local de Argentina
activity_duration = "00:30"
activity_note = "Tipo de tratamiento: Revisión dental"

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

# Función para obtener el ID del propietario dinámicamente (primer propietario activo)
def get_owner_id():
    users_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/users?api_token={PIPEDRIVE_API_KEY}'
    response = requests.get(users_url)
    if response.status_code == 200:
        users_data = response.json().get('data', [])
        for user in users_data:
            # Verificamos que el usuario esté activo
            if user.get('active_flag') == 1:
                return user['id']
        print("No se encontró un propietario activo.")
    else:
        print(f"Error al obtener los usuarios: {response.status_code}")
        print(response.text)
    return None

# Función para crear contacto
def create_patient_contact(contact_name, phone=None, email=None):
    contact_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/persons?api_token={PIPEDRIVE_API_KEY}'
    contact_data = {'name': contact_name}
    if phone:
        contact_data['phone'] = phone
    if email:
        contact_data['email'] = email

    response = requests.post(contact_url, json=contact_data)
    if response.status_code == 201:
        contact = response.json()
        if 'data' in contact:
            return contact['data']['id']
        else:
            print("Error: No se pudo obtener el ID del contacto.")
    else:
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
        lead = response.json()
        if 'data' in lead:
            return lead['data']['id']
        else:
            print("Error: No se pudo obtener el ID del lead.")
    else:
        print(f"Error al crear el lead: {response.status_code}")
        print(response.text)
    return None

# Función para verificar actividades existentes
def check_existing_appointments(due_date, due_time, duration):
    activity_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/activities?api_token={PIPEDRIVE_API_KEY}'
    response = requests.get(activity_url)
    if response.status_code == 200:
        activities = response.json().get('data', [])
        for activity in activities:
            if activity['due_date'] == due_date and activity['due_time'] == due_time:
                return True  # Ya existe una actividad en ese horario
    return False

# Función para validar si el horario está dentro del horario laboral
def is_within_working_hours(activity_due_time):
    return WORKING_HOURS_START <= activity_due_time <= WORKING_HOURS_END

# Función para crear cita dental (actividad)
def create_dental_appointment(lead_id, activity_subject, activity_type, activity_due_date, activity_due_time, activity_duration, activity_note):
    # Convertir horario de Argentina a UTC
    utc_due_time = convert_to_utc(activity_due_date, activity_due_time)

    if not is_within_working_hours(activity_due_time):  # Verificar en hora local de Argentina
        print("La cita no se puede crear porque está fuera del horario laboral.")
        return

    if check_existing_appointments(activity_due_date, utc_due_time, activity_duration):
        print("La cita no se puede crear porque ya hay una actividad programada en ese horario.")
        return

    activity_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/activities?api_token={PIPEDRIVE_API_KEY}'
    activity_data = {
        'subject': activity_subject,
        'type': activity_type,
        'due_date': activity_due_date,
        'due_time': utc_due_time,  # Guardar en UTC en Pipedrive
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

# Flujo principal
if __name__ == "__main__":
    # Paso 1: Obtener el owner_id dinámicamente
    owner_id = get_owner_id()

    if owner_id:
        # Paso 2: Ingresar los datos del contacto
        contact_name = input("Ingrese el nombre del paciente: ")
        contact_phone = input("Ingrese el teléfono del paciente: ")
        contact_email = input("Ingrese el correo electrónico del paciente: ")

        # Paso 3: Validación del horario
        activity_due_date = f"{2025}-" + input("Ingrese el mes y día de la cita (MM-DD): ")
        while True:
            activity_due_time = input("Ingrese la hora de la cita (HH:MM, entre 09:00 y 18:00): ")
            if is_within_working_hours(activity_due_time):
                break

        # Paso 4: Crear el contacto
        contact_id = create_patient_contact(contact_name, phone=contact_phone, email=contact_email)

        if contact_id:
            # Paso 5: Crear el lead para el paciente
            lead_id = create_patient_lead(contact_id, f"Lead para {contact_name}", owner_id)

            # Paso 6: Crear la cita dental para el paciente
            if lead_id:
                create_dental_appointment(lead_id, f'Cita de Revisión dental para {contact_name}', "meeting", activity_due_date, activity_due_time, "00:30", "Tipo de tratamiento: Revisión dental")
