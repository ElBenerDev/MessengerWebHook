from flask import Flask, request, jsonify
import requests
import logging
import json
from assistant_logic import handle_assistant_response  # Importa la función desde el archivo donde esté definida

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configura tu información de Zoho
ZOHO_CLIENT_ID = '1000.5AXSBZQWODTZW71NWXA6XXZT156XPX'  # Tu client ID
ZOHO_CLIENT_SECRET = '298b235a59eba2e88e8e9ca32d5e6d480023f5096b'  # Tu client secret
ZOHO_REDIRECT_URI = 'https://messengerwebhook.onrender.com/callback'  # La URL de redirección
ZOHO_ACCESS_TOKEN = None  # Inicializamos el Access Token como None
ZOHO_REFRESH_TOKEN = None  # Inicializamos el Refresh Token como None

app = Flask(__name__)

@app.route('/generate-response', methods=['POST'])
def generate_response():
    try:
        # Obtener los datos de la solicitud
        data = request.json
        logger.info(f"Datos recibidos: {data}")

        user_message = data.get('message', '')
        user_id = data.get('sender_id', '')

        # Validar que se hayan proporcionado el mensaje y el ID del usuario
        if not user_message or not user_id:
            return jsonify({"error": "Faltan parámetros"}), 400

        # Llamar a la lógica del asistente para generar la respuesta
        assistant_message, error = handle_assistant_response(user_message, user_id)

        if error:
            return jsonify({"error": error}), 500

        # Retornar la respuesta generada por el asistente
        return jsonify({"response": assistant_message})

    except Exception as e:
        logger.error(f"Error al procesar la solicitud: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "Error: No se proporcionó el código de autorización", 400

    # Intercambiar el código por un access token
    token_url = "https://accounts.zoho.com/oauth/v2/token"
    payload = {
        'client_id': ZOHO_CLIENT_ID,
        'client_secret': ZOHO_CLIENT_SECRET,
        'redirect_uri': ZOHO_REDIRECT_URI,
        'code': code,
        'grant_type': 'authorization_code'
    }

    response = requests.post(token_url, data=payload)
    if response.status_code == 200:
        # Si la solicitud es exitosa, obtén el access_token y refresh_token
        tokens = response.json()
        global ZOHO_ACCESS_TOKEN, ZOHO_REFRESH_TOKEN
        ZOHO_ACCESS_TOKEN = tokens['access_token']
        ZOHO_REFRESH_TOKEN = tokens['refresh_token']

        # Aquí puedes guardar estos tokens de forma segura o en tu base de datos

        return jsonify({
            'access_token': ZOHO_ACCESS_TOKEN,
            'refresh_token': ZOHO_REFRESH_TOKEN
        })
    else:
        return f"Error al obtener tokens: {response.text}", 400

# Ruta para obtener información del usuario en Zoho CRM
@app.route('/get-user', methods=['GET'])
def get_user_info():
    if not ZOHO_ACCESS_TOKEN:
        return jsonify({"error": "No hay acceso a Zoho. Por favor, autoriza la aplicación primero."}), 400

    url = "https://www.zohoapis.com/crm/v2/Users"
    headers = {
        'Authorization': f'Zoho-oauthtoken {ZOHO_ACCESS_TOKEN}'
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return jsonify(response.json())
    else:
        return jsonify({"error": "Error al obtener información de usuario desde Zoho CRM"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
