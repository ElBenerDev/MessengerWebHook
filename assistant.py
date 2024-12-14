from flask import Flask, request, jsonify
from openai import OpenAI
import os
import time
import json
from tokko_search import search_properties
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
assistant_id = os.getenv("ASSISTANT_ID", "asst_Q3M9vDA4aN89qQNH1tDXhjaE")

class ConversationManager:
    def __init__(self):
        self.threads = {}
        self.contexts = {}

    def get_thread_id(self, user_id):
        if user_id not in self.threads:
            thread = client.beta.threads.create()
            self.threads[user_id] = thread.id
            self.contexts[user_id] = {}
        return self.threads[user_id]

    def get_context(self, user_id):
        return self.contexts.get(user_id, {})

    def update_context(self, user_id, context):
        self.contexts[user_id] = context

conversation_manager = ConversationManager()

def extract_search_filters(message: str, context: Dict) -> Dict[str, Any]:
    """Extrae filtros de búsqueda del mensaje y contexto"""
    filters = {}

    # Detectar tipo de operación
    if re.search(r'\b(alquiler|alquilar|rentar|renta)\b', message.lower()):
        filters['operation_type'] = 'Rent'
    elif re.search(r'\b(comprar|compra|venta|vender)\b', message.lower()):
        filters['operation_type'] = 'Sale'

    # Detectar tipo de propiedad
    if re.search(r'\b(departamento|depto)\b', message.lower()):
        filters['property_type'] = 'Apartment'
    elif re.search(r'\b(casa)\b', message.lower()):
        filters['property_type'] = 'House'
    elif re.search(r'\b(local)\b', message.lower()):
        filters['property_type'] = 'Bussiness Premises'

    # Detectar ubicación
    location_match = re.search(r'en\s+([A-Za-z\s]+)', message)
    if location_match:
        filters['location'] = location_match.group(1).strip()

    # Detectar cantidad de ambientes
    rooms_match = re.search(r'(\d+)\s+ambientes?', message)
    if rooms_match:
        filters['rooms'] = int(rooms_match.group(1))

    # Detectar rango de precios
    price_match = re.search(r'hasta\s+(\d+(?:\.\d+)?)', message)
    if price_match:
        filters['max_price'] = float(price_match.group(1).replace('.', ''))

    price_match = re.search(r'desde\s+(\d+(?:\.\d+)?)', message)
    if price_match:
        filters['min_price'] = float(price_match.group(1).replace('.', ''))

    # Combinar con contexto existente
    filters.update(context)

    return filters

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
        context = conversation_manager.get_context(user_id)

        # Extraer filtros de búsqueda
        filters = extract_search_filters(message, context)
        conversation_manager.update_context(user_id, filters)

        # Verificar si el mensaje solicita una búsqueda
        if any(word in message.lower() for word in ['buscar', 'encontrar', 'mostrar', 'ver']):
            properties_message = search_properties(filters)

            # Enviar resultados al thread
            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=f"Resultados de la búsqueda:\n\n{properties_message}"
            )
        else:
            # Enviar mensaje normal al thread
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

        # Obtener la respuesta del asistente
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        for msg in messages.data:
            if msg.role == "assistant":
                return {'response': msg.content[0].text.value}

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)