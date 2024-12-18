from flask import Flask, request, jsonify
from openai import OpenAI
import os
import time
import logging
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
        # Simular preguntas y respuestas para construir los parámetros de búsqueda
        if "buscar propiedades" in message.lower():
            # Preguntar al usuario los parámetros de búsqueda
            return (
                "Por favor, proporcione los siguientes parámetros para la búsqueda:\n"
                "- Tipos de operación (IDs separados por comas, por ejemplo: 1,2):\n"
                "- Tipos de propiedad (IDs separados por comas, por ejemplo: 2,3):\n"
                "- Precio mínimo en USD (opcional):\n"
                "- Precio máximo en USD (opcional):"
            )

        # Procesar los parámetros enviados por el usuario
        if "parametros:" in message.lower():
            try:
                # Extraer los parámetros del mensaje del usuario
                params = json.loads(message.split("parametros:")[1].strip())

                # Llamar a la función de búsqueda
                results = search_properties(params)

                if "error" in results:
                    return f"Error en la búsqueda: {results['error']}"

                # Devolver los resultados al usuario
                return f"Resultados de la búsqueda:\n{json.dumps(results, indent=4)}"

            except Exception as e:
                return f"Error al procesar los parámetros: {str(e)}"

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

@app.route('/search-properties', methods=['POST'])
def search_properties_endpoint():
    """
    Endpoint para realizar la búsqueda de propiedades interactuando con el usuario.
    """
    try:
        data = request.json
        if not data or 'parameters' not in data:
            return jsonify({'error': 'No se proporcionaron parámetros de búsqueda'}), 400

        # Obtener los parámetros de búsqueda desde la solicitud
        search_params = data['parameters']

        # Llamar a la función de búsqueda en tokko_search.py
        results = search_properties(search_params)

        # Verificar si hubo un error
        if "error" in results:
            return jsonify({'error': results["error"]}), 400

        return jsonify({'results': results})

    except Exception as e:
        logger.error(f"Error en search_properties_endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)