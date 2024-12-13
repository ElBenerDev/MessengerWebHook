from flask import Flask, request, jsonify
from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import os
import requests
import json
import time

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
assistant_id = os.getenv("ASSISTANT_ID", "asst_Q3M9vDA4aN89qQNH1tDXhjaE")

# Función para extraer filtros del mensaje del usuario
def extract_filters(user_message):
    filters = {
        "price_from": 0,
        "price_to": 1000000,
        "operation_types": [],
        "property_types": [],
        "currency": "USD",
        "location": None,
    }

    if "alquiler" in user_message.lower():
        filters["operation_types"] = [2]
    elif "comprar" in user_message.lower() or "venta" in user_message.lower():
        filters["operation_types"] = [1]
    elif "alquiler temporal" in user_message.lower():
        filters["operation_types"] = [3]

    if "menos de" in user_message.lower():
        try:
            price_to = int(user_message.split("menos de")[1].split()[0].replace(",", "").replace(".", ""))
            filters["price_to"] = price_to
        except ValueError:
            pass

    if "más de" in user_message.lower():
        try:
            price_from = int(user_message.split("más de")[1].split()[0].replace(",", "").replace(".", ""))
            filters["price_from"] = price_from
        except ValueError:
            pass

    if "departamento" in user_message.lower():
        filters["property_types"].append(2)
    if "casa" in user_message.lower():
        filters["property_types"].append(3)
    if "oficina" in user_message.lower():
        filters["property_types"].append(5)

    if "en" in user_message.lower():
        try:
            location = user_message.split("en")[1].split()[0]
            filters["location"] = location
        except IndexError:
            pass

    return filters

# Función para buscar propiedades en Tokko
def search_properties(filters):
    tokko_url = "https://www.tokkobroker.com/api/v1/property/search?key=34430fc661d5b961de6fd53a9382f7a232de3ef0"

    try:
        response = requests.post(tokko_url, json=filters)
        response.raise_for_status()

        properties = response.json()
        results = []

        for property in properties.get('objects', []):
            results.append({
                'title': property.get('title', 'Sin título'),
                'price': property.get('price', 'No especificado'),
                'location': property.get('location', {}).get('address', 'Ubicación no disponible'),
                'description': property.get('description', 'Sin descripción'),
            })

        return results

    except requests.exceptions.RequestException as e:
        print(f"Error al conectarse a la API de Tokko: {e}")
        return None

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

        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )

        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )

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