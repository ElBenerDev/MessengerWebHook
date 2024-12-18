from flask import Flask, request, jsonify
from openai import OpenAI
import json
import os
import time
import logging
from tokko_search import search_properties

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
assistant_id = os.getenv("ASSISTANT_ID", "asst_Q3M9vDA4aN89qQNH1tDXhjaE")

# Diccionario para almacenar el estado de la conversación de cada usuario
user_states = {}

class ConversationManager:
    def __init__(self):
        self.threads = {}
        self.active_runs = {}

    def get_thread_id(self, user_id: str) -> str:
        if user_id not in self.threads:
            thread = client.beta.threads.create()
            self.threads[user_id] = thread.id
        return self.threads[user_id]

    def is_run_active(self, user_id: str) -> bool:
        return user_id in self.active_runs and self.active_runs[user_id] is not None

    def set_active_run(self, user_id: str, run_id: str):
        self.active_runs[user_id] = run_id

    def clear_active_run(self, user_id: str):
        self.active_runs[user_id] = None

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

def generate_response_internal(message: str, user_id: str) -> str:
    try:
        # Obtener el estado actual del usuario
        user_state = user_states.get(user_id, {"step": 0, "data": {}})

        # Paso 0: Inicio de la conversación
        if user_state["step"] == 0:
            if "buscar propiedades" in message.lower():
                user_state["step"] = 1
                user_states[user_id] = user_state
                return (
                    "Por favor, proporcione los siguientes parámetros para la búsqueda:\n"
                    "- Tipos de operación (IDs separados por comas, por ejemplo: 1,2):"
                )
            else:
                return "No entiendo tu mensaje. Por favor, escribe 'buscar propiedades' para comenzar."

        # Paso 1: Tipos de operación
        if user_state["step"] == 1:
            try:
                operation_types = [int(op.strip()) for op in message.split(",") if op.strip().isdigit()]
                if not operation_types:
                    return "Por favor, ingrese al menos un ID válido para los tipos de operación."
                user_state["data"]["operation_types"] = operation_types
                user_state["step"] = 2
                user_states[user_id] = user_state
                return (
                    "Gracias. Ahora, proporcione los IDs de los tipos de propiedad (separados por comas, por ejemplo: 2,3):"
                )
            except Exception:
                return "Hubo un error al procesar los tipos de operación. Por favor, intente de nuevo."

        # Paso 2: Tipos de propiedad
        if user_state["step"] == 2:
            try:
                property_types = [int(prop.strip()) for prop in message.split(",") if prop.strip().isdigit()]
                if not property_types:
                    return "Por favor, ingrese al menos un ID válido para los tipos de propiedad."
                user_state["data"]["property_types"] = property_types
                user_state["step"] = 3
                user_states[user_id] = user_state
                return (
                    "Gracias. Ahora, ingrese el precio mínimo en USD (opcional, puede dejarlo vacío):"
                )
            except Exception:
                return "Hubo un error al procesar los tipos de propiedad. Por favor, intente de nuevo."

        # Paso 3: Precio mínimo
        if user_state["step"] == 3:
            try:
                price_from = float(message.strip()) if message.strip() else None
                user_state["data"]["price_from"] = price_from
                user_state["step"] = 4
                user_states[user_id] = user_state
                return (
                    "Gracias. Ahora, ingrese el precio máximo en USD (opcional, puede dejarlo vacío):"
                )
            except ValueError:
                return "El precio mínimo debe ser un número válido. Por favor, intente de nuevo."

        # Paso 4: Precio máximo
        if user_state["step"] == 4:
            try:
                price_to = float(message.strip()) if message.strip() else None
                user_state["data"]["price_to"] = price_to

                # Realizar la búsqueda
                search_params = user_state["data"]
                results = search_properties(search_params)

                # Limpiar el estado del usuario
                user_states.pop(user_id, None)

                # Verificar si hubo un error
                if "error" in results:
                    return f"Error en la búsqueda: {results['error']}"

                # Devolver los resultados al usuario
                return f"Resultados de la búsqueda:\n{json.dumps(results, indent=4)}"

            except ValueError:
                return "El precio máximo debe ser un número válido. Por favor, intente de nuevo."
            except Exception as e:
                return f"Hubo un error al realizar la búsqueda: {str(e)}"

        return "No entiendo tu mensaje. Por favor, intenta de nuevo."

    except Exception as e:
        logger.error(f"Error en generate_response_internal: {str(e)}")
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