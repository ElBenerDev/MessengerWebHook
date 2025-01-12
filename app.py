from flask import Flask, request, jsonify
import logging
from assistant_logic import handle_assistant_response  # Importa la función desde el archivo donde esté definida

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/generate-response', methods=['POST'])
def generate_response():
    try:
        # Obtener los datos de la solicitud
        data = request.json
        logger.info(f"Datos recibidos: {data}")

        user_message = data.get('message', '')
        user_id = data.get('sender_id', '')

        # Validar que se hayan proporcionado el mensaje y el ID del usuario
        if not user_message or not user_id:
            return jsonify({"error": "Faltan parámetros"}), 400

        # Llamar a la lógica del asistente para generar la respuesta
        assistant_message, error = handle_assistant_response(user_message, user_id)

        if error:
            return jsonify({"error": error}), 500

        # Retornar la respuesta generada por el asistente
        return jsonify({"response": assistant_message})

    except Exception as e:
        logger.error(f"Error al procesar la solicitud: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
