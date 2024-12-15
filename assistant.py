# assistant_server.py
from flask import Flask, request, jsonify
from openai import OpenAI
import os
import time
import json
import logging
from typing import Dict, Optional, List
from tokko_search import search_properties

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
assistant_id = os.getenv("ASSISTANT_ID", "asst_Q3M9vDA4aN89qQNH1tDXhjaE")

class ConversationManager:
    def __init__(self):
        self.threads = {}
        self.active_runs = {}
        self.contexts = {}
        self.last_search = {}

    def get_thread_id(self, user_id: str) -> str:
        if user_id not in self.threads:
            thread = client.beta.threads.create()
            self.threads[user_id] = thread.id
            self.contexts[user_id] = {
                "location": None,
                "operation_type": None,
                "property_type": None,
                "price_range": None,
                "last_search_time": None
            }
        return self.threads[user_id]

    def is_run_active(self, user_id: str) -> bool:
        return user_id in self.active_runs and self.active_runs[user_id] is not None

    def set_active_run(self, user_id: str, run_id: str):
        self.active_runs[user_id] = run_id

    def clear_active_run(self, user_id: str):
        self.active_runs[user_id] = None

    def update_context(self, user_id: str, key: str, value: str):
        if user_id in self.contexts:
            self.contexts[user_id][key] = value

    def get_context(self, user_id: str) -> Dict:
        return self.contexts.get(user_id, {})

    def should_search(self, user_id: str, message: str) -> bool:
        context = self.get_context(user_id)
        search_keywords = ['buscar', 'encontrar', 'mostrar', 'ver', 'hay', 'alquiler', 'venta']

        # Verificar si el mensaje contiene palabras clave de búsqueda
        has_search_intent = any(word in message.lower() for word in search_keywords)

        # Verificar si tenemos suficiente contexto para realizar una búsqueda
        has_operation_type = context.get('operation_type') is not None

        return has_search_intent and has_operation_type

conversation_manager = ConversationManager()

def wait_for_run(thread_id: str, run_id: str, user_id: str, max_attempts: int = 60) -> bool:
    attempts = 0
    while attempts < max_attempts:
        try:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )

            if run_status.status == 'completed':
                conversation_manager.clear_active_run(user_id)
                return True
            elif run_status.status in ['failed', 'cancelled', 'expired']:
                conversation_manager.clear_active_run(user_id)
                return False

            attempts += 1
            time.sleep(1)

        except Exception as e:
            logger.error(f"Error checking run status: {str(e)}")
            conversation_manager.clear_active_run(user_id)
            return False

    conversation_manager.clear_active_run(user_id)
    return False

def update_context_from_message(message: str, user_id: str):
    """Actualiza el contexto basado en el mensaje del usuario"""
    context = conversation_manager.get_context(user_id)

    # Detectar tipo de operación
    if any(word in message.lower() for word in ['alquiler', 'alquilar', 'renta', 'rentar']):
        conversation_manager.update_context(user_id, 'operation_type', 'Alquiler')
    elif any(word in message.lower() for word in ['venta', 'comprar', 'compra']):
        conversation_manager.update_context(user_id, 'operation_type', 'Venta')

    # Detectar ubicación (ejemplo básico)
    locations = ['ballester', 'villa ballester', 'san martin']
    for location in locations:
        if location in message.lower():
            conversation_manager.update_context(user_id, 'location', location)

def generate_response_internal(message: str, user_id: str) -> str:
    try:
        thread_id = conversation_manager.get_thread_id(user_id)

        # Actualizar contexto basado en el mensaje
        update_context_from_message(message, user_id)

        if conversation_manager.is_run_active(user_id):
            return "Por favor, espera mientras proceso tu mensaje anterior."

        # Agregar el mensaje del usuario al thread
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

        conversation_manager.set_active_run(user_id, run.id)

        # Esperar la respuesta
        if not wait_for_run(thread_id, run.id, user_id):
            return "Lo siento, hubo un error al procesar tu mensaje. Por favor, intenta de nuevo."

        # Verificar si debemos realizar una búsqueda
        if conversation_manager.should_search(user_id, message):
            context = conversation_manager.get_context(user_id)
            operation_type = context.get('operation_type')
            if operation_type:
                search_results = search_properties(message)
                if search_results:
                    return search_results

        # Obtener la respuesta del asistente
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        for msg in messages.data:
            if msg.role == "assistant":
                return msg.content[0].text.value

        return "No se pudo obtener una respuesta del asistente."

    except Exception as e:
        logger.error(f"Error en generate_response_internal: {str(e)}")
        conversation_manager.clear_active_run(user_id)
        return f"Error al generar respuesta: {str(e)}"

@app.route('/generate-response', methods=['POST'])
def generate_response():
    try:
        data = request.json
        if not data or 'message' not in data or 'sender_id' not in data:
            return jsonify({'error': 'No message or sender_id provided'}), 400

        response = generate_response_internal(data['message'], data['sender_id'])
        return jsonify({'response': response})

    except Exception as e:
        logger.error(f"Error en generate_response: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)