import requests

PIPEDRIVE_API_KEY = '8f2492eead4201ac69582ee4f3dfefd13d818b79'  # Tu API token
COMPANY_DOMAIN = 'companiademuestra'  # Tu dominio de Pipedrive

# Paso 1: Crear una nueva organización (si no tienes una ya)
organization_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/organizations?api_token={PIPEDRIVE_API_KEY}'

organization_data = {
    'name': 'Nueva Organización de Ejemplo'  # El nombre de la nueva organización
}

# Realiza la solicitud POST para crear la organización
organization_response = requests.post(organization_url, json=organization_data)

if organization_response.status_code == 201:
    # Si la organización fue creada con éxito, obtenemos su ID
    organization = organization_response.json()
    organization_id = organization['data']['id']
    print(f"Organización creada exitosamente! ID: {organization_id}")

    # Paso 2: Crear un nuevo lead asociado a la organización
    lead_url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/leads?api_token={PIPEDRIVE_API_KEY}'

    lead_data = {
        'title': 'Nuevo Lead desde API',  # El título del nuevo lead
        'organization_id': organization_id  # Asociar el lead con la organización recién creada
    }

    # Realiza la solicitud POST para crear el lead
    lead_response = requests.post(lead_url, json=lead_data)

    if lead_response.status_code == 201:
        print("Lead creado exitosamente!")
        print(lead_response.json())  # Muestra la respuesta con el nuevo lead
    else:
        print(f"Error al crear el lead: {lead_response.status_code}")
        print(lead_response.text)
else:
    print(f"Error al crear la organización: {organization_response.status_code}")
    print(organization_response.text)
