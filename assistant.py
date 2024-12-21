from flask import Flask, request, jsonify
from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import os
import logging
import json
from tokko_search import fetch_search_results, get_exchange_rate

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

    logger.info(f"Parámetros antes de procesar el mensaje: {parameters}")
    logger.info(f"Mensaje recibido para actualizar parámetros: {message}")

    if "venta" in message.lower():
        parameters["operation_types"] = [1]
    if "alquiler" in message.lower():
        parameters["operation_types"] = [2]
    if "apartamento" in message.lower():
        parameters["property_types"] = [2]
    if "casa" in message.lower():
        parameters["property_types"] = [3]
    if "precio mínimo" in message.lower():
        try:
            price_from = int(message.split("precio mínimo")[-1].strip().split()[0])
            parameters["price_from"] = price_from
        except ValueError:
            logger.warning("No se pudo procesar el precio mínimo del mensaje.")
    if "precio máximo" in message.lower():
        try:
            price_to = int(message.split("precio máximo")[-1].strip().split()[0])
            parameters["price_to"] = price_to
        except ValueError:
            logger.warning("No se pudo procesar el precio máximo del mensaje.")

    if parameters["price_from"] > parameters["price_to"]:
        logger.warning("El precio mínimo es mayor que el precio máximo. Ajustando valores.")
        parameters["price_from"] = 0

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

        # Actualizar parámetros del usuario
        updated_parameters = update_user_parameters(user_id, user_message)

        # Verificar si ya se tiene toda la información necesaria
        params_complete = (
            updated_parameters["price_from"] > 0 and
            updated_parameters["price_to"] > 0 and
            "operation_types" in updated_parameters and
            "property_types" in updated_parameters
        )

        # Si no se tiene toda la información, dejar que el asistente guíe la conversación
        if not params_complete:
            event_handler = EventHandler()
            with client.beta.threads.runs.stream(
                thread_id=user_threads[user_id],
                assistant_id=assistant_id,
                event_handler=event_handler,
            ) as stream:
                stream.until_done()

            assistant_message = event_handler.assistant_message
        else:
            # Obtener el tipo de cambio
            exchange_rate = get_exchange_rate()
            if not exchange_rate:
                return jsonify({'response': "Error al obtener el tipo de cambio."}), 500

            # Convertir precios a ARS usando el tipo de cambio
            updated_parameters["price_from"] = int(updated_parameters["price_from"] * exchange_rate)
            updated_parameters["price_to"] = int(updated_parameters["price_to"] * exchange_rate)

            # Realizar la búsqueda de propiedades
            search_results = fetch_search_results(updated_parameters)
            if not search_results:
                assistant_message = "No se encontraron resultados para tu búsqueda."
            else:
                properties = search_results.get("objects", [])
                assistant_message = f"Encontré {len(properties)} propiedades:\n"
                for idx, prop in enumerate(properties, 1):
                    title = prop.get('title', 'Sin título')
                    price = prop.get('price', 'N/A')
                    currency = prop.get('currency', 'N/A')
                    assistant_message += f"{idx}. {title} - {price} {currency}\n"

    except Exception as e:
        logger.error(f"Error al generar respuesta: {str(e)}")
        return jsonify({'response': f"Error al generar respuesta: {str(e)}"}), 500

    return jsonify({'response': assistant_message})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
