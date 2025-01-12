import requests

# Datos de autenticación
PIPEDRIVE_API_KEY = '8f2492eead4201ac69582ee4f3dfefd13d818b79'  # API token de Pipedrive
COMPANY_DOMAIN = 'companiademuestra'  # Dominio de tu cuenta de Pipedrive

# Crear una nueva organización
def create_organization(name):
    organization_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/organizations?api_token={PIPEDRIVE_API_KEY}'
    organization_data = {
        'name': name  # Nombre de la organización
    }
    response = requests.post(organization_url, json=organization_data)
    if response.status_code == 201:
        organization = response.json()
        organization_id = organization['data']['id']
        print(f"Organización creada exitosamente! ID: {organization_id}")
        return organization_id
    else:
        print(f"Error al crear la organización: {response.status_code}")
        print(response.text)
        return None

# Crear un nuevo lead asociado a la organización
def create_lead(title, organization_id):
    lead_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/leads?api_token={PIPEDRIVE_API_KEY}'
    lead_data = {
        'title': title,  # Título del lead
        'organization_id': organization_id  # ID de la organización asociada
    }
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

# Crear una actividad (cita) asociada al lead
def create_activity(subject, due_date, due_time, lead_id):
    activity_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/activities?api_token={PIPEDRIVE_API_KEY}'
    activity_data = {
        'subject': subject,  # Asunto de la actividad
        'type': 'meeting',  # Tipo de actividad
        'due_date': due_date,  # Fecha de la actividad (formato YYYY-MM-DD)
        'due_time': due_time,  # Hora de la actividad (formato HH:MM)
        'duration': '01:00',  # Duración de la actividad (en formato HH:MM)
        'lead_id': lead_id  # ID del lead asociado a la actividad
    }
    response = requests.post(activity_url, json=activity_data)
    if response.status_code == 201:
        print("Actividad creada exitosamente!")
        print(response.json())
    else:
        print(f"Error al crear la actividad: {response.status_code}")
        print(response.text)

# Flujo principal
if __name__ == "__main__":
    # Paso 1: Crear una organización
    organization_name = "Nueva Organización de Ejemplo"
    organization_id = create_organization(organization_name)

    if organization_id:
        # Paso 2: Crear un lead asociado a la organización
        lead_title = "Nuevo Lead desde API"
        lead_id = create_lead(lead_title, organization_id)

        if lead_id:
            # Paso 3: Crear una actividad asociada al lead
            activity_subject = "Reunión inicial con cliente"
            activity_due_date = "2025-01-15"  # Fecha de la actividad
            activity_due_time = "17:00"  # Hora de la actividad
            create_activity(activity_subject, activity_due_date, activity_due_time, lead_id)
