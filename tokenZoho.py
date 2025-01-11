import requests

# Datos de la aplicación Zoho
client_id = '1000.5AXSBZQWODTZW71NWXA6XXZT156XPX'  # Tu Client ID
client_secret = '298b235a59eba2e88e8e9ca32d5e6d480023f5096b'  # Tu Client Secret
redirect_uri = 'https://messengerwebhook.onrender.com/callback'  # Tu Redirect URI
authorization_code = 'AUTHORIZATION_CODE'  # Reemplaza esto con el código que recibiste en la redirección

# URL para obtener el token
token_url = "https://accounts.zoho.com/oauth/v2/token"

# Cuerpo de la solicitud para obtener los tokens
payload = {
    'client_id': client_id,
    'client_secret': client_secret,
    'redirect_uri': redirect_uri,
    'code': authorization_code,
    'grant_type': 'authorization_code'
}

# Solicitar el Access Token y el Refresh Token
response = requests.post(token_url, data=payload)

# Procesar la respuesta
if response.status_code == 200:
    tokens = response.json()
    access_token = tokens['access_token']
    refresh_token = tokens['refresh_token']
    print(f"Access Token: {access_token}")
    print(f"Refresh Token: {refresh_token}")
else:
    print(f"Error al obtener los tokens: {response.text}")
