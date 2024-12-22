from flask import Flask, request, jsonify
from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import os
import logging
import requests
import json
import re

# Importar funciones de búsqueda
from tokko_search import get_exchange_rate, fetch_search_results, ask_user_for_parameters

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configura tu cliente con la API key desde el entorno
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ID del asistente
assistant_id = os.getenv("ASSISTANT_ID", "asst_QUrcIPAsQLse1tDBIzVdw5pt")

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

        # Verificar si el asistente necesita realizar una búsqueda
        if "presupuesto" in user_message.lower():
            # Extraer el presupuesto usando una expresión regular
            match = re.search(r'([\d.]+)', user_message)
            if match:
                budget_str = match.group(1).replace('.', '').replace(',', '.')
                budget = float(budget_str)
                logger.info(f"Presupuesto extraído: {budget}")

                # Obtener parámetros de búsqueda
                search_params = ask_user_for_parameters()
                if not search_params:
                    return jsonify({'response': assistant_message, 'error': "No se pudieron generar parámetros de búsqueda."}), 400

                # Actualizar rango de precios con el presupuesto del usuario
                search_params['price_to'] = int(budget)

                # Realizar la búsqueda
                search_results = fetch_search_results(search_params)
                if search_results:
                    assistant_message += "\n\nAquí te dejo algunas opciones que pueden interesarte:\n" + json.dumps(search_results, indent=4)
                else:
                    assistant_message += "\n\nNo se encontraron resultados para tu búsqueda."
            else:
                return jsonify({'response': assistant_message, 'error': "No se encontró un presupuesto válido."}), 400

    except Exception as e:
        logger.error(f"Error al generar respuesta: {str(e)}")
        return jsonify({'response': f"Error al generar respuesta: {str(e)}"}), 500

    return jsonify({'response': assistant_message})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
