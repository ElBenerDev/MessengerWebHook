import requests

# Tu API Key de Pipedrive
PIPEDRIVE_API_KEY = '8f2492eead4201ac69582ee4f3dfefd13d818b79'

# URL para obtener los negocios
url = f'https://api.pipedrive.com/v1/deals?api_token={PIPEDRIVE_API_KEY}'

# Hacer la solicitud GET
response = requests.get(url)

# Comprobar si la solicitud fue exitosa
if response.status_code == 200:
    # Si es exitosa, mostrar los negocios
    deals = response.json()
    print(deals)
else:
    print(f"Error al obtener los negocios: {response.status_code}")
