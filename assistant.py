from flask import Flask, request, jsonify
import openai
import os

app = Flask(__name__)

# Configuración de OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')  # Usar la clave de la API

# Endpoint para generar respuestas del asistente
@app.route('/generate-response', methods=['POST'])
def generate_response():
    data = request.json
    user_message = data.get('message')
    user_id = data.get('sender_id')

    if not user_message or not user_id:
        return jsonify({'response': "No se proporcionó un mensaje o ID de usuario válido."}), 400

    try:
        # Llamar a OpenAI para obtener la respuesta
        response = openai.Completion.create(
            engine="davinci",
            prompt=user_message,
            max_tokens=1024,
            n=1,
            stop=None,
            temperature=0.5,
        )
        assistant_message = response.choices[0].text.strip()
        
        # Responder al cliente con la respuesta generada
        return jsonify({'response': assistant_message}), 200

    except Exception as e:
        return jsonify({'response': f"Error al generar respuesta: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # Asegúrate de que el servidor esté escuchando en el puerto 5000
