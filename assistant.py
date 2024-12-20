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
# Diccionario para almacenar el estado de la conversación de cada usuario
user_data = {}

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

@app.route('/generate-response', methods=['POST'])
def generate_response():
    data = request.json
    user_message = data.get('message')
    user_id = data.get('sender_id')

    if not user_message or not user_id:
        return jsonify({'response': "No se proporcionó un mensaje o ID de usuario válido."}), 400

    logger.info(f"Mensaje recibido del usuario {user_id}: {user_message}")

    # Inicializar el estado del usuario si no existe
    if user_id not in user_data:
        user_data[user_id] = {
            "location": None,
            "property_type": None,
            "price_from": None,
            "price_to": None,
            "step": 0
        }

    # Manejo del flujo de conversación
    if user_data[user_id]["step"] == 0:
        user_data[user_id]["step"] += 1
        return ask_location(user_id)

    elif user_data[user_id]["step"] == 1:
        user_data[user_id]["location"] = user_message
        user_data[user_id]["step"] += 1
        return ask_property_type(user_id)

    elif user_data[user_id]["step"] == 2:
        user_data[user_id]["property_type"] = user_message
        user_data[user_id]["step"] += 1
        return ask_price_range(user_id)

    elif user_data[user_id]["step"] == 3:
        price_range = user_message.split('-')
        if len(price_range) == 2:
            user_data[user_id]["price_from"] = int(price_range[0].strip())
            user_data[user_id]["price_to"] = int(price_range[1].strip())
            user_data[user_id]["step"] += 1
            return search_properties(user_id)

    return jsonify({'response': "No entendí tu respuesta. Por favor, proporciona la información de nuevo."})

def ask_location(user_id):
    return jsonify({'response': "¿En qué ubicación estás buscando la propiedad?"})

def ask_property_type(user_id):
    return jsonify({'response': "¿Qué tipo de propiedad estás buscando? (por ejemplo, departamento, casa)"})

def ask_price_range(user_id):
    return jsonify({'response': "¿Cuál es tu rango de precios? (por ejemplo, 100000 - 200000)"})

def search_properties(user_id):
    search_params = {
        "operation_types": [2],  # Alquiler
        "property_types": [2],    # Departamentos
        "price_from": user_data[user_id]["price_from"],
        "price_to": user_data[user_id]["price_to"],
        "currency": "ARS"
    }

    logger.info(f"Parámetros de búsqueda: {search_params}")

    # Realizar la búsqueda
    search_results = fetch_search_results(search_params)
    logger.info(f"Resultados de búsqueda: {search_results}")

    if search_results and 'objects' in search_results:
        response_message = "He encontrado algunas opciones de departamentos:\n"
        for obj in search_results['objects']:
            response_message += f"**Ubicación**: {obj['address']}\n"
            response_message += f"**Precio**: {obj['price']} ARS al mes\n"
            response_message += f"**Descripción**: {obj['description']}\n"
            response_message += f"[Ver detalles]({obj['link']})\n\n"

        logger.info(f"Mensaje de respuesta al usuario: {response_message}")
        return jsonify({'response': response_message})
    else:
        logger.warning("No se encontraron resultados para la búsqueda.")
        return jsonify({'response': "No se encontraron resultados para tu búsqueda."})

def fetch_search_results(search_params):
    endpoint = "https://www.tokkobroker.com/api/v1/property/search/"
    try:
        data_param = json.dumps(search_params, separators=(',', ':'))
        logger.info(f"JSON generado para la búsqueda: {data_param}")
        params = {
            "key": os.getenv("TOKKO_API_KEY"),  # Asegúrate de tener esta variable de entorno
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
            if response.status_code == 401:
                logger.error("Error de autenticación: Verifica tu clave de API.")
            return None
    except Exception as e:
        logger.exception("Error al conectarse a la API de búsqueda.")
        return None

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)