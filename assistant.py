from flask import Flask, request, jsonify
import openai
import os

app = Flask(__name__)

# Configura tu cliente con la API key desde el entorno
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route('/generate-response', methods=['POST'])
def generate_response():
    data = request.json
    user_message = data.get('message')

    # Llamada a la API de OpenAI para generar una respuesta
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=user_message,
            max_tokens=150
        )
        assistant_message = response.choices[0].text.strip()
    except Exception as e:
        return jsonify({'response': f"Error al generar respuesta: {str(e)}"}), 500

    return jsonify({'response': assistant_message})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)