from flask import Flask, request, jsonify
from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import os
import logging
import json
import requests

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configura tu cliente con la API key desde el entorno
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ID del asistente
assistant_id = os.getenv("ASSISTANT_ID", "asst_Q3M9vDA4aN89qQNH1tDXhjaE")

# Diccionario para almacenar el thread_id de cada usuario
user_threads = {}

# Clave de la API de propiedades
API_KEY = "34430fc661d5b961de6fd53a9382f7a232de3ef0"

# URL de la API de tipo de cambio
EXCHANGE_RATE_API_URL = "https://api.exchangerate-api.com/v4/latest/USD"

# Crear un manejador de eventos para manejar el stream de respuestas del asistente
class EventHandler(AssistantEventHandler):
    def __init__(self):
        super().__init__()
        self.assistant_message = ""

    @override
    def on_text_created(self, text) -> None:
        print(f"Asistente: {text.value}", end="", flush=True)
        self.assistant_message += text.value

    @override
    def on_text_delta(self, delta, snapshot):
        print(delta.value, end="", flush=True)
        self.assistant_message += delta.value


def get_exchange_rate():
    """
    Obtiene el tipo de cambio actual de USD a ARS.
    """
    try:
        response = requests.get(EXCHANGE_RATE_API_URL)
        if response.status_code == 200:
            data = response.json()
            return data["rates"]["ARS"]  # Tipo de cambio de USD a ARS
        else:
            logging.error(f"Error al obtener el tipo de cambio. Código de estado: {response.status_code}")
            return None
    except Exception as e:
        logging.exception("Error al conectarse a la API de tipo de cambio.")
        return None


def fetch_search_results(search_params):
    """
    Función para realizar la búsqueda en la API con los parámetros seleccionados.
    """
    endpoint = "https://www.tokkobroker.com/api/v1/property/search/"
    try:
        # Convertir los parámetros a JSON
        data_param = json.dumps(search_params, separators=(',', ':'))  # Elimina espacios adicionales
        params = {
            "key": API_KEY,
            "data": data_param,
            "format": "json",
            "limit": 20
        }
        response = requests.get(endpoint, params=params)
        logger.info(f"Solicitud enviada a la API de búsqueda: {response.url}")
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"Error al realizar la búsqueda. Código de estado: {response.status_code}")
            logging.error(f"Respuesta del servidor: {response.text}")
            return None
    except Exception as e:
        logging.exception("Error al conectarse a la API de búsqueda.")
        return None


@app.route('/generate-response', methods=['POST'])
def generate_response():
    """
    Endpoint que recibe un mensaje del usuario, lo procesa con el asistente de OpenAI
    y devuelve la respuesta generada.
    """
    data = request.json
    user_id = data.get('sender_id')
    user_message = data.get('message')

    if not user_id or not user_message:
        return jsonify({'response': "Faltan el ID de usuario o el mensaje."}), 400

    # Aquí puedes agregar lógica para manejar los threads de usuario, si es necesario
    thread_id = user_threads.get(user_id)

    try:
        # Generar respuesta con el asistente de OpenAI
        response = client.Completion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": user_message}],
            assistant_id=assistant_id,
            max_tokens=150
        )

        # Obtener la respuesta del asistente
        assistant_message = response.choices[0].message['content']
        return jsonify({'response': assistant_message})

    except Exception as e:
        logging.error(f"Error al procesar la solicitud con OpenAI: {str(e)}")
        return jsonify({'response': "Error al procesar tu mensaje."}), 500


@app.route('/property-search', methods=['POST'])
def property_search():
    """
    Endpoint para realizar búsquedas en la API de propiedades.
    """
    data = request.json
    user_id = data.get('sender_id')
    search_params = data.get('search_params')

    if not user_id or not search_params:
        return jsonify({'response': "Faltan el ID de usuario o los parámetros de búsqueda."}), 400

    # Obtener tipo de cambio y ajustar parámetros de búsqueda
    exchange_rate = get_exchange_rate()
    if exchange_rate is None:
        return jsonify({'response': "Error al obtener el tipo de cambio."}), 500

    # Ajustar precios en ARS
    if 'price_from' in search_params and 'price_to' in search_params:
        search_params['price_from'] = int(search_params['price_from'] * exchange_rate)
        search_params['price_to'] = int(search_params['price_to'] * exchange_rate)

    logger.info(f"Parámetros de búsqueda ajustados: {search_params}")

    # Realizar la búsqueda
    search_results = fetch_search_results(search_params)
    if not search_results:
        return jsonify({'response': "No se encontraron resultados."}), 404

    return jsonify({'response': search_results})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)