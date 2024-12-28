from flask import Flask, request, jsonify
from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import os
import logging
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

# ID del catálogo de Facebook
CATALOG_ID = "618636270837934"

# Función para obtener productos del catálogo
def get_catalog_products():
    url = f'https://graph.facebook.com/v12.0/{CATALOG_ID}/products'
    params = {
        'access_token': os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()['data']  # Retorna los productos
    else:
        logger.error("Error al obtener productos del catálogo.")
        return []

# Crear un manejador de eventos para manejar el stream de respuestas del asistente
class EventHandler:
    def __init__(self):
        self.assistant_message = ""

    def on_text_created(self, text) -> None:
        self.assistant_message += text['value']

    def on_text_delta(self, delta) -> None:
        self.assistant_message += delta['value']

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

        # Enviar el mensaje del usuario al hilo existente
        client.beta.threads.messages.create(
            thread_id=user_threads[user_id],
            role="user",
            content=user_message
        )

        # Obtener productos del catálogo si es necesario
        products = get_catalog_products()
        catalog_info = ""
        if products:
            catalog_info = "\n".join([f"{p['name']}: {p['description']} - {p['price']} {p['currency']}" for p in products])

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
        if 'productos' in user_message.lower():
            assistant_message += "\n\nAquí están los productos disponibles:\n" + catalog_info

        logger.info(f"Mensaje generado por el asistente: {assistant_message}")

    except Exception as e:
        logger.error(f"Error al generar respuesta: {str(e)}")
        return jsonify({'response': f"Error al generar respuesta: {str(e)}"}), 500

    return jsonify({'response': assistant_message})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
