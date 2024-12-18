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

def generate_response_internal(message: str, user_id: str) -> str:
    try:
        # Aquí se puede agregar lógica adicional para manejar el mensaje
        search_results = search_properties(message)
        if search_results:
            return str(search_results)  # Asegurarse de que sea un string

        return "No se encontraron resultados para tu búsqueda."
    except Exception as e:
        logger.error(f"Error en generate_response_internal: {str(e)}")
        return f"Error al generar respuesta: {str(e)}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)