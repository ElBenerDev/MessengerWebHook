from flask import Flask, request, jsonify
from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import os
import requests
import json

app = Flask(__name__)

# Configura tu cliente con la API key desde el entorno
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ID del asistente (debe configurarse como variable de entorno o directamente aquí)
assistant_id = os.getenv("ASSISTANT_ID", "asst_Q3M9vDA4aN89qQNH1tDXhjaE")  # Cambia esto si es necesario

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

user_threads = {}  # Diccionario global para almacenar hilos por usuario

@app.route('/generate-response', methods=['POST'])
def generate_response():
    data = request.json
    user_message = data.get('message')
    user_id = data.get('user_id')  # Identificador único del usuario

    if not user_message or not user_id:
        return jsonify({'response': "No se proporcionó un mensaje o un ID de usuario válido."}), 400

    try:
        # Verificar si el hilo ya existe para el usuario
        thread_id = user_threads.get(user_id)
        if not thread_id:
            thread = client.beta.threads.create()
            print("Hilo creado:", thread)

            if not thread or not hasattr(thread, "id"):
                raise ValueError("No se pudo crear el hilo de conversación.")

            thread_id = thread.id
            user_threads[user_id] = thread_id

        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
        )

        event_handler = EventHandler()
        with client.beta.threads.runs.stream(
            thread_id=thread_id,
            assistant_id=assistant_id,
            event_handler=event_handler,
        ) as stream:
            stream.until_done()

        assistant_message = event_handler.assistant_message

        if not assistant_message:
            raise ValueError("El asistente no generó un mensaje.")

    except Exception as e:
        return jsonify({'response': f"Error al generar respuesta: {str(e)}"}), 500

    return jsonify({'response': assistant_message})

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

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        print(f"Mensaje enviado a {sender_id}: {message}")
    else:
        print(f"Error al enviar mensaje a {sender_id}: {response.text}")

@app.route('/webhook', methods=['POST'])
def webhook():
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
                            response = client.post(
                                f'{os.getenv("PYTHON_SERVICE_URL")}/generate-response',
                                json={'message': received_message, 'user_id': sender_id}
                            )
                            assistant_message = response.json().get('response', "No se pudo generar una respuesta.")
                            send_message_to_whatsapp(sender_id, assistant_message, value['metadata']['phone_number_id'])

                        except Exception as e:
                            print(f"Error al interactuar con el servicio Python: {e}")
                            send_message_to_whatsapp(sender_id, "Lo siento, hubo un problema al procesar tu mensaje.", value['metadata']['phone_number_id'])
                    else:
                        print(f"El mensaje no es de tipo 'text': {json.dumps(message, indent=2)}")
                else:
                    print(f"El campo 'messages' no está presente o no es un array: {json.dumps(value, indent=2)}")

    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)