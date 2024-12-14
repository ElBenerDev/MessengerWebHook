from flask import Flask, request, jsonify
from openai import OpenAI
import os
import time
import json
from tokko_search import extract_filters, search_properties
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
assistant_id = os.getenv("ASSISTANT_ID", "asst_Q3M9vDA4aN89qQNH1tDXhjaE")

class ConversationManager:
    def __init__(self):
        self.threads = {}

    def get_thread_id(self, user_id):
        if user_id not in self.threads:
            thread = client.beta.threads.create()
            self.threads[user_id] = thread.id
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

    try:
        thread_id = conversation_manager.get_thread_id(user_id)

        # Verificar y esperar cualquier ejecución pendiente
        runs = client.beta.threads.runs.list(thread_id=thread_id)
        for run in runs.data:
            if run.status not in ['completed', 'failed', 'cancelled', 'expired']:
                if not wait_for_run(thread_id, run.id):
                    return {'response': "Lo siento, hubo un error al procesar tu mensaje (timeout)."}

        # Crear el nuevo mensaje del usuario
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )

        # Crear y ejecutar el run
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )

        if not wait_for_run(thread_id, run.id):
            return {'response': "Lo siento, hubo un error al procesar tu mensaje (timeout)."}

        # Verificar si el asistente solicitó una búsqueda
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        for message in messages.data:
            if message.role == "assistant":
                content = message.content[0].text.value
                if "search_properties" in content:
                    try:
                        # Extraer el contexto de la búsqueda
                        search_start = content.find("{")
                        search_end = content.rfind("}") + 1
                        if search_start != -1 and search_end != -1:
                            context = json.loads(content[search_start:search_end])

                            # Realizar la búsqueda
                            filters = extract_filters(context)
                            properties_data = search_properties(filters)

                            # Añadir los resultados al thread
                            if properties_data:
                                formatted_message = json.dumps(properties_data)
                                client.beta.threads.messages.create(
                                    thread_id=thread_id,
                                    role="user",
                                    content=formatted_message
                                )

                                # Crear nuevo run para procesar los resultados
                                run = client.beta.threads.runs.create(
                                    thread_id=thread_id,
                                    assistant_id=assistant_id
                                )

                                if not wait_for_run(thread_id, run.id):
                                    return {'response': "Error al procesar los resultados de la búsqueda."}

                                # Obtener la respuesta final
                                final_messages = client.beta.threads.messages.list(thread_id=thread_id)
                                for final_message in final_messages.data:
                                    if final_message.role == "assistant":
                                        return {'response': final_message.content[0].text.value}
                    except json.JSONDecodeError:
                        logger.error("Error al decodificar el contexto de búsqueda")

                return {'response': content}

        return {'response': "No se pudo obtener una respuesta del asistente."}

    except Exception as e:
        logger.error(f"Error en generate_response_internal: {str(e)}")
        return {'response': f"Error al generar respuesta: {str(e)}"}

@app.route('/generate-response', methods=['POST'])
def generate_response():
    try:
        data = request.json
        if not data or 'message' not in data or 'sender_id' not in data:
            return jsonify({'error': 'No message or sender_id provided'}), 400

        response_data = generate_response_internal(data['message'], data['sender_id'])
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error en generate_response: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode and token:
        if mode == 'subscribe' and token == os.getenv('FACEBOOK_VERIFY_TOKEN'):
            return challenge
        else:
            return 'Forbidden', 403

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)