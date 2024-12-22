from flask import Flask, request, jsonify
from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import os
import logging
import requests
import json

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

# Función para obtener el tipo de cambio
def get_exchange_rate():
    EXCHANGE_RATE_API_URL = "https://api.exchangerate-api.com/v4/latest/USD"
    try:
        response = requests.get(EXCHANGE_RATE_API_URL)
        if response.status_code == 200:
            data = response.json()
            return data["rates"]["ARS"]  # Tipo de cambio de USD a ARS
        else:
            logger.error(f"Error al obtener el tipo de cambio. Código de estado: {response.status_code}")
            return None
    except Exception as e:
        logger.exception("Error al conectarse a la API de tipo de cambio.")
        return None

# Función para realizar la búsqueda de propiedades
def fetch_search_results(search_params):
    endpoint = "https://www.tokkobroker.com/api/v1/property/search/"
    try:
        data_param = json.dumps(search_params, separators=(',', ':'))  # Elimina espacios adicionales
        params = {
            "key": os.getenv("PROPERTY_API_KEY"),  # Asegúrate de tener esta clave en tus variables de entorno
            "data": data_param,
            "format": "json",
            "limit": 20
        }
        response = requests.get(endpoint, params=params)
        logger.info(f"Solicitud enviada a la API de búsqueda: {response.url}")
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error al realizar la búsqueda. Código de estado: {response.status_code}")
            return None
    except Exception as e:
        logger.exception("Error al conectarse a la API de búsqueda.")
        return None

@app.route('/generate-response', methods=['POST'])
def generate_response():
    data = request.json
    user_message = data.get('message')
    user_id = data.get('sender_id')

    if not user_message or not user_id:
        return jsonify({'response': "No se proporcionó un mensaje o ID de usuario válido."}), 400

    logger.info(f"Mensaje recibido del usuario {user_id}: {user_message}")

    # Responder al usuario sin importar el mensaje
    response_message = "Gracias por tu mensaje. Estoy buscando propiedades ahora."

    # Ejecutar la búsqueda con parámetros predeterminados
    operation_ids = [2]  # Solo Rent
    property_ids = [2]   # Solo Apartment

    # Obtener el tipo de cambio
    exchange_rate = get_exchange_rate()
    if not exchange_rate:
        return jsonify({'response': "No se pudo obtener el tipo de cambio."}), 500

    # Rango de precios predeterminado (en USD convertido a ARS)
    price_from = int(0 * exchange_rate)
    price_to = int(500 * exchange_rate)

    # Construir los parámetros de búsqueda
    search_params = {
        "operation_types": operation_ids,
        "property_types": property_ids,
        "price_from": price_from,
        "price_to": price_to,
        "currency": "ARS"  # La búsqueda se realiza en ARS
    }

    # Realizar la búsqueda con los parámetros seleccionados
    logger.info("Realizando la búsqueda con los parámetros predeterminados...")
    search_results = fetch_search_results(search_params)

    if not search_results:
        return jsonify({'response': "No se pudieron obtener resultados desde la API de búsqueda."}), 500

    # Mostrar los resultados de la búsqueda
    response_message += "\nAquí están los resultados de la búsqueda:\n" + json.dumps(search_results, indent=4)

    logger.info(f"Mensaje generado por el asistente: {response_message}")
    return jsonify({'response': response_message})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)