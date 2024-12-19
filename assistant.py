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

def parse_search_parameters(user_message):
    # Aquí puedes implementar la lógica para extraer los parámetros de búsqueda del mensaje del usuario
    # Por simplicidad, asumimos que el mensaje contiene los parámetros en un formato específico
    # Ejemplo: "Buscar propiedades en Buenos Aires, precio mínimo 100000, precio máximo 200000"

    # Este es un ejemplo simple de cómo podrías extraer información
    # En un caso real, deberías usar un parser más robusto o NLP
    operation_ids = [2]  # Solo alquiler por defecto
    property_ids = [2]   # Solo departamentos por defecto
    price_from = None
    price_to = None

    # Extraer precios del mensaje
    if "precio mínimo" in user_message:
        price_from = int(user_message.split("precio mínimo")[-1].split(",")[0].strip())
    if "precio máximo" in user_message:
        price_to = int(user_message.split("precio máximo")[-1].split(",")[0].strip())

    exchange_rate = get_exchange_rate()
    if exchange_rate:
        price_from = int(price_from * exchange_rate) if price_from else None
        price_to = int(price_to * exchange_rate) if price_to else None

    search_params = {
        "operation_types": operation_ids,
        "property_types": property_ids,
        "price_from": price_from,
        "price_to": price_to,
        "currency": "ARS"
    }

    return {k: v for k, v in search_params.items() if v is not None}

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
        else:
            thread_id = user_threads[user_id]

        # Parsear los parámetros de búsqueda del mensaje del usuario
        search_params = parse_search_parameters(user_message)
        if search_params:
            search_results = fetch_search_results(search_params)
            if search_results and 'objects' in search_results:
                assistant_message = "Resultados de la búsqueda:\n"
                for obj in search_results['objects']:
                    for operation in obj.get('operations', []):
                        if operation['operation_id'] == 2:  # Asegurarse de que sea alquiler
                            price = operation['prices'][0]['price']
                            assistant_message += f"Ubicación: {obj['address']}\n"
                            assistant_message += f"Precio: {price} ARS al mes\n"
                            assistant_message += f"Descripción: {obj['description']}\n"
                            assistant_message += f"Link: https://ficha.info/p/{obj['id']}\n"
                            assistant_message += "-----\n"
                logger.info(f"Mensaje generado por el asistente: {assistant_message}")
            else:
                assistant_message = "No se encontraron resultados para su búsqueda."
        else:
            assistant_message = "No se pudieron procesar los parámetros de búsqueda."

    except Exception as e:
        logger.error(f"Error al generar respuesta: {str(e)}")
        return jsonify({'response': f"Error al generar respuesta: {str(e)}"}), 500

    return jsonify({'response': assistant_message})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)