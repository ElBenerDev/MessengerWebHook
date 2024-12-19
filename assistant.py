from flask import Flask, request, jsonify
from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import os
import json
import logging
from tokko_search import search_properties, format_properties_message  # Importar la lógica de búsqueda y formateo

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configura tu cliente con la API key desde el entorno
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ID del asistente (debe configurarse como variable de entorno o directamente aquí)
assistant_id = os.getenv("ASSISTANT_ID", "asst_Q3M9vDA4aN89qQNH1tDXhjaE")  # Cambia esto si es necesario

# Diccionario para almacenar el estado de la conversación de cada usuario
user_states = {}

# Diccionario para almacenar el thread_id de cada usuario
user_threads = {}

# Crear un manejador de eventos para manejar el stream de respuestas del asistente
class EventHandler(AssistantEventHandler):
    def __init__(self):
        super().__init__()
        self.assistant_message = ""  # Almacena el mensaje generado por el asistente

    @override
    def on_text_created(self, text) -> None:
        # Este evento se dispara cuando se crea texto en el flujo
        if text.value not in self.assistant_message:
            print(f"Asistente: {text.value}", end="", flush=True)
            self.assistant_message += text.value  # Agregar el texto al mensaje final

    @override
    def on_text_delta(self, delta, snapshot):
        # Este evento se dispara cuando el texto cambia o se agrega en el flujo
        if delta.value not in self.assistant_message:
            print(delta.value, end="", flush=True)
            self.assistant_message += delta.value  # Agregar el texto al mensaje final

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
            # Crear un nuevo hilo de conversación si no existe
            thread = client.beta.threads.create()
            logger.info(f"Hilo creado para el usuario {user_id}: {thread.id}")

            # Verificar que el hilo se creó correctamente
            if not thread or not hasattr(thread, "id"):
                raise ValueError("No se pudo crear el hilo de conversación.")

            # Guardar el thread_id para este usuario
            user_threads[user_id] = thread.id

        # Obtener el thread_id del usuario
        thread_id = user_threads[user_id]

        # Verificar si hay una ejecución activa
        if thread_id in user_states and user_states[thread_id] == "active":
            logger.warning(f"El hilo {thread_id} ya tiene una ejecución activa. Ignorando el nuevo mensaje.")
            return jsonify({'response': "Por favor, espera a que se complete la respuesta anterior."}), 429

        # Marcar el hilo como activo
        user_states[thread_id] = "active"

        # Enviar el mensaje del usuario al hilo existente
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
        )

        # Crear y manejar la respuesta del asistente
        event_handler = EventHandler()  # Instancia del manejador de eventos
        with client.beta.threads.runs.stream(
            thread_id=thread_id,
            assistant_id=assistant_id,
            event_handler=event_handler,
        ) as stream:
            stream.until_done()  # Esperar a que el flujo termine

        # Obtener el mensaje generado por el asistente
        assistant_message = event_handler.assistant_message
        logger.info(f"Mensaje generado por el asistente: {assistant_message}")

        # Marcar el hilo como inactivo
        user_states[thread_id] = "inactive"

        # Devolver la respuesta generada por el asistente
        return jsonify({'response': assistant_message})

    except Exception as e:
        # Capturar cualquier error y devolverlo como respuesta
        logger.error(f"Error al generar respuesta: {str(e)}")
        return jsonify({'response': f"Error al generar respuesta: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)