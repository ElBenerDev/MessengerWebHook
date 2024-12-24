import os
import logging
import requests
import json
import time
from flask import Flask, request, jsonify
from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override

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

    try:
        # Verificar si ya existe un thread_id para este usuario
        if user_id not in user_threads:
            # Crear un nuevo hilo de conversación si no existe
            thread = client.beta.threads.create()
            logger.info(f"Hilo creado para el usuario {user_id}: {thread.id}")
            user_threads[user_id] = thread.id
        else:
            thread_id = user_threads[user_id]

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
        assistant_message = event_handler.assistant_message
        logger.info(f"Mensaje generado por el asistente: {assistant_message}")

        # Si el presupuesto ha sido proporcionado, ejecutar la búsqueda
        if 'presupuesto' in data:
            user_budget = data.get('presupuesto')

            # Obtener el tipo de cambio
            exchange_rate = get_exchange_rate()
            if not exchange_rate:
                return jsonify({'response': "No se pudo obtener el tipo de cambio."}), 500

            # Modificar el parámetro de búsqueda con el presupuesto del usuario
            price_from = 0
            price_to = int(user_budget * exchange_rate)

            # Parámetros de búsqueda
            search_params = {
                "operation_types": [1],  # Solo Rent
                "property_types": [2],   # Solo Apartment
                "price_from": price_from,
                "price_to": price_to,
                "currency": "ARS"  # La búsqueda se realiza en ARS
            }

            # Verificación de búsqueda
            logger.info(f"Realizando búsqueda con parámetros: {search_params}")

            # Realizar la búsqueda con los parámetros seleccionados
            search_results = fetch_search_results(search_params)

            if not search_results:
                return jsonify({'response': "No se encontraron propiedades dentro de ese presupuesto."}), 500

            # Mensaje de respuesta con los resultados encontrados
            response_message = "Aquí tienes los resultados de la búsqueda con tu presupuesto máximo:"
            for property in search_results.get('properties', []):
                property_message = f"\n- **Tipo de propiedad:** {property.get('property_type')}\n" \
                                   f"- **Ubicación:** {property.get('location')}\n" \
                                   f"- **Precio:** {property.get('price')} ARS\n" \
                                   f"- **Habitaciones:** {property.get('rooms')}\n" \
                                   f"- **Detalles:** {property.get('details')}\n" \
                                   f"[Ver más detalles]({property.get('url')})"
                response_message += property_message
                time.sleep(1)  # Esperar un segundo entre mensajes (opcional)

            # Limpiar datos del usuario después de la búsqueda
            del user_threads[user_id]

            # Retornar el mensaje final junto con los resultados de búsqueda
            return jsonify({'response': assistant_message + response_message})

        # Si el presupuesto no ha sido proporcionado aún, el asistente pregunta
        else:
            return jsonify({'response': assistant_message})

    except Exception as e:
        logger.error(f"Error al generar respuesta: {str(e)}")
        return jsonify({'response': f"Error al generar respuesta: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
