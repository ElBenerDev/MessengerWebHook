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

# Clave de la API de propiedades
API_KEY = "34430fc661d5b961de6fd53a9382f7a232de3ef0"
EXCHANGE_RATE_API_URL = "https://api.exchangerate-api.com/v4/latest/USD"

def get_exchange_rate():
    try:
        response = requests.get(EXCHANGE_RATE_API_URL)
        if response.status_code == 200:
            data = response.json()
            return data["rates"]["ARS"]
        else:
            logger.error(f"Error al obtener el tipo de cambio. Código de estado: {response.status_code}")
            return None
    except Exception as e:
        logger.exception("Error al conectarse a la API de tipo de cambio.")
        return None

def fetch_search_results(search_params):
    endpoint = "https://www.tokkobroker.com/api/v1/property/search/"
    try:
        data_param = json.dumps(search_params, separators=(',', ':'))
        logger.info(f"JSON generado para la búsqueda: {data_param}")
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
            logger.error(f"Error al realizar la búsqueda. Código de estado: {response.status_code}")
            logger.error(f"Respuesta del servidor: {response.text}")
            return None
    except Exception as e:
        logger.exception("Error al conectarse a la API de búsqueda.")
        return None

def ask_user_for_parameters(user_id):
    # Preguntar al usuario sobre los parámetros de búsqueda
    return {
        "operation_types": [2],  # Solo alquiler por defecto
        "property_types": [2],    # Solo departamentos por defecto
        "price_from": None,
        "price_to": None,
        "currency": "ARS"
    }

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

@app.route('/generate-response', methods=['POST'])
def generate_response():
    data = request.json
    user_message = data.get('message')
    user_id = data.get('sender_id')

    if not user_message or not user_id:
        return jsonify({'response': "No se proporcionó un mensaje o ID de usuario válido."}), 400

    logger.info(f"Mensaje recibido del usuario {user_id}: {user_message}")

    try:
        # Verificar si ya existe un thread_id para este usuario
        if user_id not in user_threads:
            thread = client.beta.threads.create()
            logger.info(f"Hilo creado para el usuario {user_id}: {thread.id}")
            user_threads[user_id] = thread.id

        # Aquí se puede implementar la lógica de descubrimiento
        if "hola" in user_message.lower():
            assistant_message = "¡Hola! ¿Qué tipo de propiedad estás buscando? (por ejemplo, alquiler de departamentos)"
        elif "departamento" in user_message.lower():
            assistant_message = "Entendido, ¿cuál es tu rango de precios? (por ejemplo, entre 100000 y 200000)"
        elif "precio" in user_message.lower():
            # Aquí podrías preguntar más detalles
            assistant_message = "Perfecto, ¿tienes un precio mínimo y máximo en mente?"
        elif "como te llamas" in user_message.lower():
            assistant_message = "Soy un asistente virtual aquí para ayudarte a encontrar propiedades."
        else:
            # Si no se entiende el mensaje, se puede pedir más información
            assistant_message = "No entendí tu solicitud. ¿Puedes darme más detalles sobre lo que buscas?"

        # Enviar el mensaje del asistente
        logger.info(f"Mensaje generado por el asistente: {assistant_message}")

    except Exception as e:
        logger.error(f"Error al generar respuesta: {str(e)}")
        return jsonify({'response': f"Error al generar respuesta: {str(e)}"}), 500

    return jsonify({'response': assistant_message})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)