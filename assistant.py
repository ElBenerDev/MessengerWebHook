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

# Diccionario para almacenar el estado de cada usuario
user_state = {}
user_threads = {}

# Crear un manejador de eventos para manejar el stream de respuestas del asistente
class EventHandler(AssistantEventHandler):
    def __init__(self, user_id):
        super().__init__()
        self.assistant_message = ""
        self.user_id = user_id

    @override
    def on_text_created(self, text) -> None:
        print(f"Asistente: {text.value}", end="", flush=True)
        self.assistant_message += text.value

        # Verificar si el asistente terminó de preguntar
        if "¿Cuál es tu presupuesto máximo?" in text.value:
            user_state[self.user_id]["ready_for_search"] = True

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
            return data["rates"]["ARS"]
        else:
            logger.error(f"Error al obtener el tipo de cambio. Código de estado: {response.status_code}")
            return None
    except Exception as e:
        logger.exception("Error al conectarse a la API de tipo de cambio.")
        return None

# Función para realizar la búsqueda de propiedades
def fetch_search_results():
    endpoint = "https://www.tokkobroker.com/api/v1/property/search/"
    try:
        # Obtener tipo de cambio
        exchange_rate = get_exchange_rate()
        if not exchange_rate:
            logger.error("No se pudo obtener el tipo de cambio.")
            return None

        # Parámetros de búsqueda
        operation_ids = [1]  # Solo Rent
        property_ids = [2]   # Solo Apartment
        price_from = int(0 * exchange_rate)
        price_to = int(5000000 * exchange_rate)

        search_params = {
            "operation_types": operation_ids,
            "property_types": property_ids,
            "price_from": price_from,
            "price_to": price_to,
            "currency": "ARS"
        }

        data_param = json.dumps(search_params, separators=(',', ':'))
        params = {
            "key": os.getenv("PROPERTY_API_KEY"),
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

    try:
        # Verificar si ya existe un thread_id para este usuario
        if user_id not in user_threads:
            thread = client.beta.threads.create()
            logger.info(f"Hilo creado para el usuario {user_id}: {thread.id}")
            user_threads[user_id] = thread.id
        else:
            logger.info(f"Usando hilo existente para el usuario {user_id}: {user_threads[user_id]}")

        # Enviar el mensaje del usuario al hilo existente
        client.beta.threads.messages.create(
            thread_id=user_threads[user_id],
            role="user",
            content=user_message
        )

        # Crear y manejar la respuesta del asistente
        event_handler = EventHandler()
        with client.beta.threads.runs.stream(
            thread_id=user_threads[user_id],
            assistant_id=assistant_id,
            event_handler=event_handler,
        ) as stream:
            stream.until_done()

        # Obtener el mensaje generado por el asistente
        assistant_message = event_handler.assistant_message.strip()
        logger.info(f"Mensaje generado por el asistente: {assistant_message}")

        # Validar si el mensaje está vacío
        if not assistant_message:
            logger.warning("El asistente no generó una respuesta válida.")
            assistant_message = "Parece que no puedo responder en este momento. Por favor, intenta más tarde."

    except Exception as e:
        logger.error(f"Error al generar respuesta: {str(e)}", exc_info=True)
        return jsonify({'response': f"Error al generar respuesta: {str(e)}"}), 500

    return jsonify({'response': assistant_message})



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
