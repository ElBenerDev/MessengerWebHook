from flask import Flask, request, jsonify
from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import os
import logging
from tokko_search import ask_user_for_parameters, fetch_search_results  # Importar funciones de búsqueda

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

@app.route('/generate-response', methods=['POST'])
def generate_response():
    data = request.json
    user_message = data.get('message')
    user_id = data.get('sender_id')

    if not user_message or not user_id:
        return jsonify({'response': "No se proporcionó un mensaje o ID de usuario válido."}), 400

    logger.info(f"Mensaje recibido del usuario {user_id}: {user_message}")

    # Lógica para interactuar con el usuario y recolectar datos
    if "tipo de cambio" in user_message.lower():
        return jsonify({'response': "¿En qué moneda te gustaría saber el tipo de cambio? (por ejemplo, USD a ARS)"})

    if "buscar propiedades" in user_message.lower():
        return jsonify({'response': "¿En qué ciudad deseas buscar propiedades? ¿Cuál es tu rango de precio?"})

    # Nueva lógica para manejar la búsqueda de propiedades
    if "en" in user_message.lower() and "habitaciones" in user_message.lower() and "usd" in user_message.lower():
        # Extraer información de la búsqueda
        # Ejemplo: "en ballester, 2 habitaciones y 5000 USD al mes"
        # Aquí deberías implementar un parser para extraer la ciudad, habitaciones y precio
        # Para simplificar, asumiremos que el formato es siempre el mismo
        try:
            # Extraer parámetros de búsqueda
            parts = user_message.split(",")
            location = parts[0].replace("en", "").strip()  # Ciudad
            room_info = parts[1].strip()  # Habitaciones y precio
            num_rooms = int(room_info.split("habitaciones")[0].strip())
            budget = int(room_info.split("USD")[0].split()[-1].strip())

            # Generar parámetros de búsqueda
            search_params = {
                "operation_types": [2],  # Solo Rent
                "property_types": [2],    # Solo Apartment
                "price_from": 0,          # Puedes ajustar esto según sea necesario
                "price_to": budget,       # Presupuesto máximo
                "currency": "USD",        # La búsqueda se realiza en USD
                "location": location,      # Ciudad
                "rooms": num_rooms         # Habitaciones
            }

            # Realizar la búsqueda
            search_results = fetch_search_results(search_params)
            if search_results:
                response_message = "Aquí tienes algunas opciones de departamentos en alquiler:\n"
                for idx, property in enumerate(search_results.get('properties', []), start=1):
                    response_message += f"{idx}. **{property['title']}**\n"
                    response_message += f"   - **Dirección:** {property['address']}\n"
                    response_message += f"   - **Precio:** {property['price']} ARS al mes\n"
                    response_message += f"   - **Detalles:** [Ver más detalles]({property['link']})\n"
                    response_message += f"   - ![Foto]({property['image']})\n\n"
                return jsonify({'response': response_message})
            else:
                return jsonify({'response': "No se encontraron propiedades que coincidan con tus criterios."})

        except Exception as e:
            logger.error(f"Error al procesar la búsqueda: {str(e)}")
            return jsonify({'response': "Hubo un error al procesar tu solicitud de búsqueda."}), 500

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

    except Exception as e:
        logger.error(f"Error al generar respuesta: {str(e)}")
        return jsonify({'response': f"Error al generar respuesta: {str(e)}"}), 500

    return jsonify({'response': assistant_message})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)