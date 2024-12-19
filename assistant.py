from flask import Flask, request, jsonify
from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import os
import json
import logging
from tokko_search import fetch_search_results, format_properties_message, ask_user_for_parameters

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configura tu cliente con la API key desde el entorno
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ID del asistente
assistant_id = os.getenv("ASSISTANT_ID", "asst_Q3M9vDA4aN89qQNH1tDXhjaE")

# Diccionario para almacenar el estado de la conversación de cada usuario
user_states = {}

# Diccionario para almacenar el thread_id de cada usuario
user_threads = {}

class EventHandler(AssistantEventHandler):
    def __init__(self):
        super().__init__()
        self.assistant_message = ""

    @override
    def on_text_created(self, text) -> None:
        if text.value not in self.assistant_message:
            print(f"Asistente: {text.value}", end="", flush=True)
            self.assistant_message += text.value

    @override
    def on_text_delta(self, delta, snapshot):
        if delta.value not in self.assistant_message:
            print(delta.value, end="", flush=True)
            self.assistant_message += delta.value

@app.route('/generate-response', methods=['POST'])
def generate_response():
    data = request.json
    user_message = data.get('message')
    user_id = data.get('sender_id')

    logger.info(f"Mensaje recibido del usuario {user_id}: {user_message}")

    if not user_message or not user_id:
        return jsonify({'response': "No se proporcionó un mensaje o ID de usuario válido."}), 400

    try:
        # Verificar si ya existe un thread_id para este usuario
        if user_id not in user_threads:
            thread = client.beta.threads.create()
            logger.info(f"Hilo creado para el usuario {user_id}: {thread.id}")
            user_threads[user_id] = thread.id

        thread_id = user_threads[user_id]

        # Verificar si hay una ejecución activa
        if user_states.get(thread_id) == "active":
            logger.warning(f"El hilo {thread_id} ya tiene una ejecución activa. Ignorando el nuevo mensaje.")
            return jsonify({'response': "Estamos procesando tu solicitud anterior. Por favor, espera un momento."}), 429

        # Marcar el hilo como activo
        user_states[thread_id] = "active"

        # Enviar el mensaje del usuario al hilo existente
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
        )

        # Crear y manejar la respuesta del asistente
        event_handler = EventHandler()
        with client.beta.threads.runs.stream(
            thread_id=thread_id,
            assistant_id=assistant_id,
            event_handler=event_handler,
        ) as stream:
            stream.until_done()

        assistant_message = event_handler.assistant_message
        logger.info(f"Mensaje generado por el asistente: {assistant_message}")

        # Lógica para buscar propiedades
        if "quiero alquilar" in user_message.lower() or "quiero comprar" in user_message.lower():
            search_params = ask_user_for_parameters(user_message)
            if search_params:
                search_results = fetch_search_results(search_params)
                formatted_message = format_properties_message(search_results)
                assistant_message += f"\n\n{formatted_message}"
        else:
            assistant_message += "\n\n¡Hola! ¿En qué puedo ayudarte hoy? Si buscas propiedades, por favor indícame cuántas habitaciones necesitas y tu presupuesto."

        # Marcar el hilo como inactivo
        user_states[thread_id] = "inactive"

        return jsonify({'response': assistant_message})

    except Exception as e:
        logger.error(f"Error al generar respuesta: {str(e)}")
        return jsonify({'response': f"Error al generar respuesta: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)