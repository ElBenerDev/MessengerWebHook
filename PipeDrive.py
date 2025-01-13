import requests

# Datos de autenticación
PIPEDRIVE_API_KEY = '8f2492eead4201ac69582ee4f3dfefd13d818b79'  # API token de Pipedrive
COMPANY_DOMAIN = 'companiademuestra'  # Dominio de tu cuenta de Pipedrive

# Crear un contacto (persona) para el paciente
def create_patient_contact(patient_name, phone=None, email=None):
    contact_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/persons?api_token={PIPEDRIVE_API_KEY}'
    
    contact_data = {
        'name': patient_name,  # Nombre del paciente
    }
    
    # Agregar teléfono y correo electrónico si se proporcionan
    if phone:
        contact_data['phone'] = phone
    if email:
        contact_data['email'] = email
    
    response = requests.post(contact_url, json=contact_data)
    if response.status_code == 201:
        contact = response.json()
        contact_id = contact['data']['id']
        print(f"Contacto creado exitosamente! ID: {contact_id}")
        return contact_id
    else:
        print(f"Error al crear el contacto: {response.status_code}")
        print(response.text)
        return None

# Crear un nuevo lead para el paciente
def create_patient_lead(patient_name, contact_id, treatment_type=None):
    lead_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/leads?api_token={PIPEDRIVE_API_KEY}'
    
    lead_data = {
        'title': patient_name,  # Nombre del paciente
        'person_id': contact_id  # ID del contacto (persona) asociado al lead
    }
    
    # Agregar tipo de tratamiento si se proporciona
    if treatment_type:
        lead_data['custom_fields'] = {'treatment_type': treatment_type}  # Tipo de tratamiento
    
    response = requests.post(lead_url, json=lead_data)
    if response.status_code == 201:
        lead = response.json()
        lead_id = lead['data']['id']
        print(f"Lead creado exitosamente! ID: {lead_id}")
        return lead_id
    else:
        print(f"Error al crear el lead: {response.status_code}")
        print(response.text)
        return None

# Crear una actividad de cita dental
def create_dental_appointment(lead_id, treatment_type, appointment_date, appointment_time):
    activity_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/activities?api_token={PIPEDRIVE_API_KEY}'
    
    activity_data = {
        'subject': f'Cita de {treatment_type} para {lead_id}',  # Asunto de la actividad: Cita con el paciente
        'type': 'meeting',  # Tipo de actividad (puede ser "meeting" para citas)
        'due_date': appointment_date,  # Fecha de la cita (YYYY-MM-DD)
        'due_time': appointment_time,  # Hora de la cita (HH:MM)
        'duration': '00:30',  # Duración de la cita, puede ajustarse según sea necesario
        'lead_id': lead_id  # ID del lead (paciente) asociado
    }
    
    response = requests.post(activity_url, json=activity_data)
    if response.status_code == 201:
        print("Cita dental creada exitosamente!")
        print(response.json())
    else:
        print(f"Error al crear la cita dental: {response.status_code}")
        print(response.text)

# Flujo principal
if __name__ == "__main__":
    # Paso 1: Crear un contacto para el paciente (dentista)
    patient_name = "Juan Pérez"
    patient_phone = "+1234567890"
    patient_email = "juan.perez@email.com"
    treatment_type = "Revisión dental"
    
    contact_id = create_patient_contact(patient_name, phone=patient_phone, email=patient_email)

    # Paso 2: Crear el lead para el paciente
    if contact_id:
        lead_id = create_patient_lead(patient_name, contact_id, treatment_type)

        # Paso 3: Crear la cita dental para el paciente
        if lead_id:
            appointment_date = "2025-01-15"  # Fecha de la cita
            appointment_time = "10:00"  # Hora de la cita
            create_dental_appointment(lead_id, treatment_type, appointment_date, appointment_time)
