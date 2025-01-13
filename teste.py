import requests

PIPEDRIVE_API_KEY = '8f2492eead4201ac69582ee4f3dfefd13d818b79'
COMPANY_DOMAIN = 'companiademuestra'

def get_lead_fields():
    url = f'https://{COMPANY_DOMAIN}.pipedrive.com/v1/leadFields?api_token={PIPEDRIVE_API_KEY}'
    response = requests.get(url)
    if response.status_code == 200:
        fields = response.json()['data']
        for field in fields:
            print(f"ID: {field['key']}, Nombre: {field['name']}")
        return fields
    else:
        print(f"Error al obtener los campos: {response.status_code}")
        print(response.text)
        return None

if __name__ == "__main__":
    get_lead_fields()
