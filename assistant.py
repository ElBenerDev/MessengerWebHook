from flask import Flask, request, jsonify, send_from_directory
from gtts import gTTS
import os
import logging
import requests

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configura tu cliente con la API key desde el entorno
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
CATALOG_ID = "618636270837934"  # ID del catálogo de Facebook

# Diccionario para almacenar el thread_id de cada usuario
user_threads = {}

# Función para obtener productos del catálogo
def get_catalog_products():
    url = f'https://graph.facebook.com/v12.0/{CATALOG_ID}/products'
    params = {
        'access_token': FACEBOOK_PAGE_ACCESS_TOKEN
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()['data']  # Retorna los productos
    else:
        logger.error("Error al obtener productos del catálogo. Respuesta: %s", response.text)
        return []

# Función para generar audio desde texto
def generate_audio(text, filename='response.mp3'):
    tts = gTTS(text, lang='es')  # Cambiar el idioma según necesites
    tts.save(filename)
    return filename

@app.route('/generate-response', methods=['POST'])
def generate_response():
    data = request.json
    user_message = data.get('message')
    user_id = data.get('sender_id')

    if not user_message or not user_id:
        return jsonify({'response': "No se proporcionó un mensaje o ID de usuario válido."}), 400

    logger.info(f"Mensaje recibido del usuario {user_id}: {user_message}")

    try:
        # Lógica de generación de respuesta (aquí puedes conectar con tu modelo de OpenAI)
        assistant_message = "Esta es una respuesta generada por el asistente."

        # Convertir la respuesta a audio
        audio_filename = generate_audio(assistant_message)
        audio_url = f"http://<your_server_address>/audio/{audio_filename}"  # Asegúrate de que esté accesible en la web

        logger.info(f"Mensaje generado por el asistente: {assistant_message}")

    except Exception as e:
        logger.error(f"Error al generar respuesta: {str(e)}")
        return jsonify({'response': f"Error al generar respuesta: {str(e)}"}), 500

    return jsonify({'response': assistant_message, 'audio_url': audio_url})

# Servir los archivos de audio
@app.route('/audio/<filename>')
def serve_audio(filename):
    return send_from_directory('path_to_audio_directory', filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
