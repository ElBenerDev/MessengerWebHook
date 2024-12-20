from flask import Flask, request, jsonify
from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import os
import logging
import json

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configura tu cliente con la API key desde el entorno
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ID del asistente
assistant_id = os.getenv("ASSISTANT_ID", "asst_Q3M9vDA4aN89qQNH1tDXhjaE")

# Diccionario para almacenar el thread_id de cada usuario y sus parámetros
user_threads = {}
user_parameters = {}

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

def update_user_parameters(user_id, message):
    """
    Actualiza los parámetros del usuario en función del mensaje proporcionado.
    """
    if user_id not in user_parameters:
        # Inicializar parámetros predeterminados
        user_parameters[user_id] = {
            "operation_types": [2],  # Predeterminado: Rent
            "property_types": [2],   # Predeterminado: Apartment
            "price_from": 0,        # Precio mínimo en USD
            "price_to": 10000       # Precio máximo en USD
        }

    parameters = user_parameters[user_id]

    # Logs para entender qué parámetros se están actualizando
    logger.info(f"Parámetros antes de procesar el mensaje: {parameters}")
    logger.info(f"Mensaje recibido para actualizar parámetros: {message}")

    # Procesar el mensaje del usuario para actualizar parámetros
    try:
        if message.isdigit():
            # Si el mensaje es un número, se asume como precio máximo
            parameters["price_to"] = int(message)
        elif "venta" in message.lower():
            parameters["operation_types"] = [1]  # Sale
        elif "alquiler" in message.lower():
            parameters["operation_types"] = [2]  # Rent
        elif "apartamento" in message.lower():
            parameters["property_types"] = [2]  # Apartment
        elif "casa" in message.lower():
            parameters["property_types"] = [3]  # House
        elif "precio mínimo" in message.lower():
            try:
                price_from = int(message.split("precio mínimo")[-1].strip().split()[0])
                parameters["price_from"] = price_from
            except ValueError:
                logger.warning("No se pudo procesar el precio mínimo del mensaje.")
        elif "precio máximo" in message.lower():
            try:
                price_to = int(message.split("precio máximo")[-1].strip().split()[0])
                parameters["price_to"] = price_to
            except ValueError:
                logger.warning("No se pudo procesar el precio máximo del mensaje.")
    except Exception as e:
        logger.error(f"Error al procesar parámetros: {str(e)}")

    logger.info(f"Parámetros actualizados: {parameters}")
    return parameters


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

        # Actualizar parámetros del usuario según el mensaje
        updated_parameters = update_user_parameters(user_id, user_message)

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

        # Agregar los parámetros actualizados a la respuesta
        assistant_message += f"\n\nParámetros actuales: {json.dumps(updated_parameters, indent=2)}"
        logger.info(f"Mensaje generado por el asistente: {assistant_message}")

    except Exception as e:
        logger.error(f"Error al generar respuesta: {str(e)}")
        return jsonify({'response': f"Error al generar respuesta: {str(e)}"}), 500

    return jsonify({'response': assistant_message})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
