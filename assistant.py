from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Variable para almacenar los threads
threads = {}

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if data and 'entry' in data:
        for entry in data['entry']:
            changes = entry.get('changes', [])
            for change in changes:
                value = change.get('value', {})
                if 'messages' in value:
                    messages = value['messages']
                    for message in messages:
                        if message.get('type') == 'text':
                            sender_id = message['from']
                            message_body = message['text']['body']
                            phone_number_id = value['metadata']['phone_number_id']
                            print(f"[0] Mensaje recibido de {sender_id}: {message_body}")

                            # Procesar el mensaje con el servicio de respuesta
                            try:
                                response = requests.post(
                                    f"{os.getenv('PYTHON_SERVICE_URL')}/generate-response",
                                    json={
                                        'user_id': sender_id,
                                        'message': message_body
                                    }
                                )
                                if response.status_code == 200:
                                    assistant_message = response.json().get('response', "No se pudo generar una respuesta.")
                                else:
                                    assistant_message = "Error al obtener la respuesta del servicio."

                                # Enviar mensaje de respuesta a WhatsApp
                                send_message(sender_id, assistant_message, phone_number_id)

                            except Exception as e:
                                print(f"[0] Error al interactuar con el servicio Python: {e}")
                                send_message(sender_id, "Lo siento, hubo un problema al procesar tu mensaje.", phone_number_id)
                        else:
                            print(f"[0] El mensaje no es de tipo 'text' o tiene un formato no compatible: {message}")

    return jsonify({'status': 'success'}), 200


@app.route('/generate-response', methods=['POST'])
def generate_response():
    data = request.json
    user_id = data.get('user_id')
    message = data.get('message')

    if not user_id or not message:
        return jsonify({'error': 'Faltan datos obligatorios: user_id o message'}), 400

    # Manejo de hilos
    thread = threads.get(user_id)
    if not thread:
        thread = {'messages': []}
        threads[user_id] = thread

    thread['messages'].append({'role': 'user', 'content': message})

    # Simulación de respuesta generada por un asistente (para prueba)
    assistant_response = f"Hola, procesé tu mensaje: {message}"

    # Guardar la respuesta del asistente
    thread['messages'].append({'role': 'assistant', 'content': assistant_response})

    return jsonify({'response': assistant_response}), 200


def send_message(recipient_id, message, phone_number_id):
    url = f"https://graph.facebook.com/v17.0/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "text": {"body": message}
    }
    headers = {
        "Authorization": f"Bearer {os.getenv('WHATSAPP_API_KEY')}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        print(f"[0] Mensaje enviado a {recipient_id}: {message}")
    else:
        print(f"[0] Error al enviar mensaje a {recipient_id}: {response.text}")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)