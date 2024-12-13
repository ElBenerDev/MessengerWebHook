from flask import Flask, request, jsonify
from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import os
import json
import time
from tokko_search import extract_filters, search_properties

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
assistant_id = os.getenv("ASSISTANT_ID", "asst_Q3M9vDA4aN89qQNH1tDXhjaE")

class ConversationManager:
    def __init__(self):
        self.threads = {}
        print("ConversationManager inicializado")

    def get_thread_id(self, user_id):
        if user_id not in self.threads:
            thread = client.beta.threads.create()
            self.threads[user_id] = thread.id
            print(f"Nuevo thread creado para usuario {user_id}: {thread.id}")
        return self.threads[user_id]

conversation_manager = ConversationManager()

def wait_for_run(thread_id, run_id, max_wait_seconds=30):
    start_time = time.time()
    while True:
        if time.time() - start_time > max_wait_seconds:
            return False

        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run_id
        )
        if run_status.status == 'completed':
            return True
        elif run_status.status in ['failed', 'cancelled', 'expired']:
            return False
        time.sleep(1)

def generate_response_internal(message, user_id):
    if not message or not user_id:
        return {'response': "No se proporcionó un mensaje o un ID de usuario válido."}

    # Verificar si el mensaje solicita una búsqueda de propiedades
    if "buscar propiedades" in message.lower() or "quiero alquilar" in message.lower() or "quiero comprar" in message.lower():
        filters = extract_filters(message)
        properties = search_properties(filters)

        if properties is None:
            return {'response': "No se pudo realizar la búsqueda de propiedades en este momento."}

        response_message = "Aquí tienes algunas propiedades disponibles:\n"
        for property in properties:
            response_message += f"- **{property['title']}**\n"
            response_message += f"  Precio: {property['price']}\n"
            response_message += f"  Ubicación: {property['location']}\n"
            response_message += f"  Descripción: {property['description']}\n\n"

        return {'response': response_message}

    try:
        thread_id = conversation_manager.get_thread_id(user_id)

        # Verificar y esperar cualquier ejecución pendiente
        runs = client.beta.threads.runs.list(thread_id=thread_id)
        for run in runs.data:
            if run.status not in ['completed', 'failed', 'cancelled', 'expired']:
                if not wait_for_run(thread_id, run.id):
                    return {'response': "Lo siento, hubo un error al procesar tu mensaje (timeout)."}

        # Ahora podemos crear el nuevo mensaje
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )

        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )

        if not wait_for_run(thread_id, run.id):
            return {'response': "Lo siento, hubo un error al procesar tu mensaje (timeout)."}

        messages = client.beta.threads.messages.list(
            thread_id=thread_id
        )

        for message in messages.data:
            if message.role == "assistant":
                return {'response': message.content[0].text.value}

        return {'response': "No se pudo obtener una respuesta del asistente."}

    except Exception as e:
        print(f"Error en generate_response_internal: {str(e)}")
        return {'response': f"Error al generar respuesta: {str(e)}"}

@app.route('/generate-response', methods=['POST'])
def generate_response():
    try:
        print("Datos recibidos:", request.json)
        data = request.json
        if not data or 'message' not in data or 'sender_id' not in data:
            print("Faltan campos requeridos:", data)
            return jsonify({'error': 'No message or sender_id provided'}), 400

        message = data['message']
        sender_id = data['sender_id']

        response_data = generate_response_internal(message, sender_id)
        return jsonify(response_data)

    except Exception as e:
        print(f"Error en generate_response: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode and token:
        if mode == 'subscribe' and token == os.getenv('FACEBOOK_VERIFY_TOKEN'):
            print("Webhook verificado!")
            return challenge
        else:
            return 'Forbidden', 403

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)