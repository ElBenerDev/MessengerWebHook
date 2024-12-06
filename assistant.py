import os
import json
import requests
from flask import Flask, request, jsonify
from openai import OpenAI
from openai import AssistantEventHandler

app = Flask(__name__)

# Configura tu cliente con la API key desde el entorno
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

assistant_id = os.getenv("ASSISTANT_ID", "asst_Q3M9vDA4aN89qQNH1tDXhjaE")

# Variable global para almacenar el thread_id activo
active_thread_id = None

# Handler personalizado para manejar los eventos del asistente de OpenAI
class EventHandler(AssistantEventHandler):
    def __init__(self):
        super().__init__()
        self.assistant_message = ""

    def on_text_created(self, text) -> None:
        print(f"Asistente: {text.value}", end="", flush=True)
        self.assistant_message += text.value


@app.route('/generate-response', methods=['POST'])
def generate_response():
    global active_thread_id

    # Log del cuerpo recibido
    print("Datos recibidos en /generate-response:", request.json)

    data = request.json
    user_message = data.get('message')

    if not user_message:
        return jsonify({'error': "No se proporcionó un mensaje válido."}), 400

    # Filtrar el comando para "buscar propiedades"
    if "buscar propiedades" in user_message.lower():
        # Extrae filtros y busca propiedades (esto lo debes definir en tu lógica)
        filters = extract_filters(user_message)
        properties = search_properties(filters)

        if not properties:
            return jsonify({'response': "No se encontraron propiedades que coincidan con la búsqueda."}), 404

        response_message = "Propiedades encontradas:\n"
        for property in properties:
            title = property.get("title", "Sin título")
            description = property.get("description", "Sin descripción")
            location = property.get("fake_address", "Sin ubicación")
            operation = "Alquiler" if "Rent" in [op["operation_type"] for op in property["operations"]] else "Venta"
            price = next(
                (op["prices"][0]["price"] for op in property["operations"] if op["operation_type"] in ["Rent", "Sale"]),
                "No disponible"
            )

            response_message += (
                f"- **{title}**\n"
                f"  Operación: {operation}\n"
                f"  Precio: {price}\n"
                f"  Ubicación: {location}\n"
                f"  Descripción: {description}\n\n"
            )

        return jsonify({'response': response_message})

    return jsonify({'response': "Comando no reconocido."}), 400


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print(f"Datos recibidos en webhook: {json.dumps(data, indent=2)}")

    if 'entry' in data:
        for entry in data['entry']:
            changes = entry.get('changes', [])
            for change in changes:
                value = change.get('value', {})

                # Filtrar eventos de estado
                if value.get('statuses'):
                    print(f"Evento de estado recibido: {json.dumps(value['statuses'], indent=2)}")
                    continue  # Ignorar eventos de estado

                # Verificar que el mensaje sea de tipo 'text'
                if 'messages' in value and isinstance(value['messages'], list):
                    message = value['messages'][0]
                    if message.get('type') == 'text':
                        sender_id = message['from']
                        received_message = message['text']['body']
                        print(f"Mensaje recibido de {sender_id}: {received_message}")

                        try:
                            # Realizar la llamada al endpoint de Python para obtener la respuesta
                            response = client.post(
                                f'{os.getenv("PYTHON_SERVICE_URL")}/generate-response',
                                json={'message': received_message}
                            )

                            # Asegurarse de que la respuesta sea válida
                            assistant_message = response.json().get('response', "No se pudo generar una respuesta.")
                            
                            # Aquí debes llamar a la función para enviar el mensaje de vuelta a WhatsApp
                            send_message_to_whatsapp(sender_id, assistant_message, value['metadata']['phone_number_id'])

                        except Exception as e:
                            print(f"Error al interactuar con el servicio Python: {e}")
                            send_message_to_whatsapp(sender_id, "Lo siento, hubo un problema al procesar tu mensaje.", value['metadata']['phone_number_id'])

                    else:
                        # Si no es un mensaje de texto, imprimir el error
                        print(f"El mensaje no es de tipo 'text': {json.dumps(message, indent=2)}")
                else:
                    print(f"El campo 'messages' no está presente o no es un array: {json.dumps(value, indent=2)}")

    return jsonify({'status': 'success'})


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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
