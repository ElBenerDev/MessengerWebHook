from flask import Flask, request, jsonify
from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import os
from search_functions import extract_filters, search_properties  # Importar las funciones de búsqueda

app = Flask(__name__)

# Configura tu cliente con la API key desde el entorno
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ID del asistente (debe configurarse como variable de entorno o directamente aquí)
assistant_id = os.getenv("ASSISTANT_ID", "asst_Q3M9vDA4aN89qQNH1tDXhjaE")  # Cambia esto si es necesario

# Variable global para almacenar el thread_id activo
active_thread_id = None

# Crear un manejador de eventos para manejar el stream de respuestas del asistente
class EventHandler(AssistantEventHandler):
    def __init__(self):
        super().__init__()  # Inicializar correctamente la clase base
        self.assistant_message = ""  # Almacena el mensaje generado por el asistente

    @override
    def on_text_created(self, text) -> None:
        # Este evento se dispara cuando se crea texto en el flujo
        print(f"Asistente: {text.value}", end="", flush=True)
        self.assistant_message += text.value  # Agregar el texto al mensaje final

    @override
    def on_text_delta(self, delta, snapshot):
        # Este evento se dispara cuando el texto cambia o se agrega en el flujo
        print(delta.value, end="", flush=True)
        self.assistant_message += delta.value  # Agregar el texto al mensaje final

@app.route('/generate-response', methods=['POST'])
def generate_response():
    global active_thread_id  # Usar la variable global para almacenar el thread_id

    data = request.json
    user_message = data.get('message')

    if not user_message:
        return jsonify({'response': "No se proporcionó un mensaje válido."}), 400

    # Verificar si el mensaje solicita una búsqueda de propiedades
    if "buscar propiedades" in user_message.lower() or "quiero alquilar" in user_message.lower() or "quiero comprar" in user_message.lower():
        # Extraer filtros del mensaje del usuario
        filters = extract_filters(user_message)

        # Realizar la búsqueda de propiedades
        properties = search_properties(filters)

        if properties is None:
            return jsonify({'response': "No se pudo realizar la búsqueda de propiedades en este momento."}), 500

        # Formatear los resultados para enviarlos al usuario
        response_message = "Aquí tienes algunas propiedades disponibles:\n"
        for property in properties:
            response_message += f"- **{property['title']}**\n"
            response_message += f"  Precio: {property['price']}\n"
            response_message += f"  Ubicación: {property['location']}\n"
            response_message += f"  Descripción: {property['description']}\n\n"

        return jsonify({'response': response_message})

    try:
        # Crear un nuevo hilo si no existe uno activo
        if not active_thread_id:
            thread = client.beta.threads.create()
            active_thread_id = thread.id  # Guardar el thread_id activo
            print(f"Hilo creado: {thread}")
        else:
            print(f"Reutilizando hilo existente: {active_thread_id}")

        # Enviar el mensaje del usuario al hilo activo
        client.beta.threads.messages.create(
            thread_id=active_thread_id,
            role="user",
            content=user_message
        )

        # Crear y manejar la respuesta del asistente
        event_handler = EventHandler()  # Instancia del manejador de eventos
        with client.beta.threads.runs.stream(
            thread_id=active_thread_id,
            assistant_id=assistant_id,
            event_handler=event_handler,
        ) as stream:
            stream.until_done()  # Esperar a que el flujo termine

        # Obtener el mensaje generado por el asistente
        assistant_message = event_handler.assistant_message

    except Exception as e:
        # Capturar cualquier error y devolverlo como respuesta
        return jsonify({'response': f"Error al generar respuesta: {str(e)}"}), 500

    return jsonify({'response': assistant_message})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)