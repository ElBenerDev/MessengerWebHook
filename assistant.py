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
        print("ConversationManager inicializado")

    def get_thread_id(self, user_id):
        if user_id not in self.threads:
            thread = client.beta.threads.create()
            self.threads[user_id] = thread.id
            print(f"Nuevo thread creado para usuario {user_id}: {thread.id}")
        return self.threads[user_id]

# Inicializar el manejador de conversaciones
conversation_manager = ConversationManager()

def generate_response_internal(message, user_id):
    if not message or not user_id:
        return {'response': "No se proporcionó un mensaje o un ID de usuario válido."}

    try:
        # Obtener el thread existente o crear uno nuevo
        thread_id = conversation_manager.get_thread_id(user_id)

        # Enviar el mensaje del usuario al hilo
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )

        # Crear un run
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )

        # Esperar a que el run se complete
        while True:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            if run_status.status == 'completed':
                break
            elif run_status.status == 'failed':
                return {'response': "Lo siento, hubo un error al procesar tu mensaje."}
            time.sleep(1)

        # Obtener los mensajes
        messages = client.beta.threads.messages.list(
            thread_id=thread_id
        )

        # Obtener la última respuesta del asistente
        for message in messages.data:
            if message.role == "assistant":
                return {'response': message.content[0].text.value}

        return {'response': "No se pudo obtener una respuesta del asistente."}

    except Exception as e:
        print(f"Error en generate_response_internal: {str(e)}")
        return {'response': f"Error al generar respuesta: {str(e)}"}

def send_message_to_whatsapp(sender_id, message, phone_number_id):
    url = f'https://graph.facebook.com/v15.0/{phone_number_id}/messages'
    payload = {
        "messaging_product": "whatsapp",
        "to": sender_id,
        "text": {"body": message}
    }
    headers = {
        "Authorization": f"Bearer {os.getenv('FACEBOOK_PAGE_ACCESS_TOKEN')}",
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

@app.route('/generate-response', methods=['POST'])
def generate_response():
    try:
        data = request.json
        if not data or 'message' not in data or 'sender_id' not in data:
            return jsonify({'error': 'No message or sender_id provided'}), 400

        message = data['message']
        sender_id = data['sender_id']

        response_data = generate_response_internal(message, sender_id)
        return jsonify(response_data)

    except Exception as e:
        print(f"Error en generate_response: {str(e)}")
        return jsonify({'error': str(e)}), 500

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
                            except Exception as e:
                                print(f"Error al procesar el mensaje: {e}")
                                if value.get('metadata', {}).get('phone_number_id'):
                                    send_message_to_whatsapp(
                                        sender_id, 
                                        "Lo siento, hubo un problema al procesar tu mensaje.", 
                                        value['metadata']['phone_number_id']
                                    )

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
        if mode == 'subscribe' and token == os.getenv('FACEBOOK_VERIFY_TOKEN'):
            print("Webhook verificado!")
            return challenge
        else:
            return 'Forbidden', 403

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)