import requests

PIPEDRIVE_API_KEY = '8f2492eead4201ac69582ee4f3dfefd13d818b79'
COMPANY_DOMAIN = 'companiademuestra'

# Función para obtener los campos personalizados de Pipedrive para los leads
def get_custom_fields():
    url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/dealFields?api_token={PIPEDRIVE_API_KEY}'
    response = requests.get(url)
    
    if response.status_code == 200:
        # Si la respuesta es exitosa, mostramos los campos disponibles
        custom_fields_data = response.json()
        print(custom_fields_data)  # Esto te dará toda la estructura de la respuesta.
    else:
        print(f"Error al obtener los campos personalizados: {response.text}")

# Llamamos a la función
get_custom_fields()
