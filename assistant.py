from flask import Flask, request, jsonify
from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import os
import requests
import json
import time

app = Flask(__name__)

# Configuración inicial
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
assistant_id = os.getenv("ASSISTANT_ID", "asst_Q3M9vDA4aN89qQNH1tDXhjaE")

class ConversationManager:
    def __init__(self):
        self.threads = {}
        self.last_activity = {}
        print("ConversationManager inicializado")

    def get_thread_id(self, user_id):
        try:
            # Primero, buscar threads existentes con el metadata del usuario
            if user_id in self.threads:
                thread_id = self.threads[user_id]
                try:
                    # Verificar si el thread existe
                    thread = client.beta.threads.retrieve(thread_id)
                    if thread.metadata.get('user_id') == user_id:
                        print(f"Reutilizando thread existente {thread_id} para usuario {user_id}")
                        self.last_activity[user_id] = time.time()
                        return thread_id
                except Exception:
                    # Si el thread no existe, eliminarlo del diccionario
                    del self.threads[user_id]

            # Si no se encontró un thread válido, crear uno nuevo
            print(f"Creando nuevo thread para usuario {user_id}")
            thread = client.beta.threads.create(
                metadata={'user_id': user_id}
            )
            self.threads[user_id] = thread.id
            self.last_activity[user_id] = time.time()
            return thread.id

        except Exception as e:
            print(f"Error en get_thread_id: {str(e)}")
            # En caso de error, crear un nuevo thread
            thread = client.beta.threads.create(
                metadata={'user_id': user_id}
            )
            self.threads[user_id] = thread.id
            self.last_activity[user_id] = time.time()
            return thread.id

    def cleanup_old_threads(self, max_age=3600):
        current_time = time.time()
        for user_id in list(self.threads.keys()):
            if current_time - self.last_activity.get(user_id, 0) > max_age:
                try:
                    thread_id = self.threads[user_id]
                    client.beta.threads.delete(thread_id)
                except Exception:
                    pass
                finally:
                    del self.threads[user_id]
                    del self.last_activity[user_id]

# Inicializar el manejador de conversaciones
conversation_manager = ConversationManager()

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

def generate_response_internal(message, user_id):
    """Función interna para generar respuestas sin hacer llamadas HTTP"""
    if not message or not user_id:
        raise ValueError("No se proporcionó un mensaje o un ID de usuario válido.")

    try:
        # Obtener el thread existente o crear uno nuevo
        thread_id = conversation_manager.get_thread_id(user_id)
        print(f"Usando thread {thread_id} para usuario {user_id}")

        # Crear el mensaje en el thread
        message_obj = client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )

        # Crear y ejecutar el run
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )

        # Esperar la respuesta
        max_retries = 10
        retry_count = 0
        while retry_count < max_retries:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            if run_status.status == 'completed':
                break
            elif run_status.status == 'failed':
                raise Exception("La ejecución del asistente falló")
            time.sleep(1)
            retry_count += 1

        if retry_count >= max_retries:
            raise Exception("Tiempo de espera agotado")

        # Obtener los mensajes más recientes
        messages = client.beta.threads.messages.list(
            thread_id=thread_id,
            order="desc",
            limit=1
        )

        if not messages.data:
            raise Exception("No se recibió respuesta del asistente")

        assistant_message = messages.data[0].content[0].text.value

        return {'response': assistant_message}

    except Exception as e:
        print(f"Error en generate_response_internal: {str(e)}")
        raise

@app.route('/generate-response', methods=['POST'])
def generate_response():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No se proporcionaron datos JSON'}), 400

        user_message = data.get('message')
        user_id = data.get('user_id')

        if not user_message or not user_id:
            return jsonify({'error': "No se proporcionó un mensaje o un ID de usuario válido."}), 400

        response_data = generate_response_internal(user_message, user_id)
        return jsonify(response_data)
    except Exception as e:
        print(f"Error en generate_response: {str(e)}")
        return jsonify({'error': f"Error al generar respuesta: {str(e)}"}), 500

def send_message_to_whatsapp(sender_id, message, phone_number_id):
    url = f'https://graph.facebook.com/v15.0/{phone_number_id}/messages'
    payload = {
        "messaging_product": "whatsapp",
        "to": sender_id,
        "text": {"body": message}
    }
    headers = {
        "Authorization": f"Bearer {os.getenv('WHATSAPP_API_KEY')}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        print(f"Mensaje enviado a {sender_id}: {message}")
        print(f"Respuesta de WhatsApp: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"Error al enviar mensaje a {sender_id}: {str(e)}")
        return None

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        print(f"Datos recibidos en webhook: {json.dumps(data, indent=2)}")

        if 'entry' in data:
            for entry in data['entry']:
                changes = entry.get('changes', [])
                for change in changes:
                    value = change.get('value', {})
                    if value.get('statuses'):
                        print(f"Evento de estado recibido: {json.dumps(value['statuses'], indent=2)}")
                        continue

                    if 'messages' in value and isinstance(value['messages'], list):
                        message = value['messages'][0]
                        if message.get('type') == 'text':
                            sender_id = message['from']
                            received_message = message['text']['body']
                            print(f"Mensaje recibido de {sender_id}: {received_message}")

                            try:
                                response_data = generate_response_internal(received_message, sender_id)
                                assistant_message = response_data.get('response', "No se pudo generar una respuesta.")
                                if value.get('metadata', {}).get('phone_number_id'):
                                    send_message_to_whatsapp(
                                        sender_id, 
                                        assistant_message, 
                                        value['metadata']['phone_number_id']
                                    )
                                else:
                                    print("Error: No se encontró phone_number_id en los metadatos")
                            except Exception as e:
                                print(f"Error al procesar el mensaje: {e}")
                                if value.get('metadata', {}).get('phone_number_id'):
                                    send_message_to_whatsapp(
                                        sender_id, 
                                        "Lo siento, hubo un problema al procesar tu mensaje.", 
                                        value['metadata']['phone_number_id']
                                    )
                        else:
                            print(f"El mensaje no es de tipo 'text': {json.dumps(message, indent=2)}")
                    else:
                        print(f"El campo 'messages' no está presente o no es un array: {json.dumps(value, indent=2)}")

        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error en webhook: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode and token:
        if mode == 'subscribe' and token == os.getenv('WEBHOOK_VERIFY_TOKEN'):
            print("Webhook verificado!")
            return challenge
        else:
            return 'Forbidden', 403

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)