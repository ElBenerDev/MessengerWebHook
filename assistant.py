from flask import Flask, request, jsonify
from openai import OpenAI
from openai import AssistantEventHandler
import os
from search_functions import extract_filters, search_properties
import json

app = Flask(__name__)

# Configura tu cliente con la API key desde el entorno
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

assistant_id = os.getenv("ASSISTANT_ID", "asst_Q3M9vDA4aN89qQNH1tDXhjaE")

# Variable global para almacenar el thread_id activo
active_thread_id = None

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

    # Si el mensaje es una búsqueda de propiedades
    if "buscar propiedades" in user_message.lower():
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

    # Si el mensaje no es una búsqueda, enviarlo al asistente
    try:
        event_handler = EventHandler()
        client.create_assistant_message(
            assistant_id=assistant_id,
            user_message=user_message,
            event_handler=event_handler
        )
        return jsonify({'response': event_handler.assistant_message})
    except Exception as e:
        print(f"Error al interactuar con el asistente: {str(e)}")
        return jsonify({'response': "Lo siento, hubo un problema al procesar tu mensaje."}), 500


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
                    continue  # Ignorar eventos de estado

                if 'messages' in value and isinstance(value['messages'], list):
                    message = value['messages'][0]
                    if message.get('type') == 'text':
                        sender_id = message['from']
                        received_message = message['text']['body']
                        print(f"Mensaje recibido de {sender_id}: {received_message}")

                        try:
                            response = client.post(
                                f'{os.getenv("PYTHON_SERVICE_URL")}/generate-response',
                                json={'message': received_message}
                            )

                            assistant_message = response.json().get('response', "No se pudo generar una respuesta.")
                            # Aquí debes llamar a la función para enviar el mensaje de vuelta a WhatsApp
                            send_message_to_whatsapp(sender_id, assistant_message, value['metadata']['phone_number_id'])

                        except Exception as e:
                            print(f"Error al interactuar con el servicio Python: {e}")
                            send_message_to_whatsapp(sender_id, "Lo siento, hubo un problema al procesar tu mensaje.", value['metadata']['phone_number_id'])

                    else:
                        print(f"El mensaje no es de tipo 'text': {json.dumps(message, indent=2)}")
                else:
                    print(f"El campo 'messages' no está presente o no es un array: {json.dumps(value, indent=2)}")

    return jsonify({'status': 'success'})


def send_message_to_whatsapp(sender_id, message, phone_number_id):
    # Aquí va la lógica para enviar el mensaje de vuelta a WhatsApp usando la API de WhatsApp
    pass


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
