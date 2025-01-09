from flask import Flask, request, jsonify
import os

app = Flask(__name__)

@app.route('/generate-response', methods=['POST'])
def generate_response():
    try:
        data = request.json
        print(f"Datos recibidos en Python: {data}")  # Añadir log aquí

        message = data.get('message', '')
        sender_id = data.get('sender_id', '')

        if not message or not sender_id:
            return jsonify({"error": "Missing parameters"}), 400

        # Aquí va la lógica para generar la respuesta
        response = f"Respuesta generada para el mensaje: '{message}'"
        return jsonify({"response": response})

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
