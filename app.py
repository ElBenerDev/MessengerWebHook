from flask import Flask, request, jsonify
import os
from assistant_logic import handle_assistant_response  # Aquí importa la función que maneja la lógica del asistente

app = Flask(__name__)

@app.route('/generate-response', methods=['POST'])
def generate_response():
    try:
        data = request.json
        print(f"Datos recibidos en Python: {data}")

        user_message = data.get('message', '')
        user_id = data.get('sender_id', '')

        if not user_message or not user_id:
            return jsonify({"error": "Missing parameters"}), 400

        # Llamar a la lógica del asistente
        assistant_message, error = handle_assistant_response(user_message, user_id)

        if error:
            return jsonify({"error": error}), 500

        return jsonify({"response": assistant_message})

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
