import requests
import os
import tempfile
import shutil
from gtts import gTTS
from flask import Flask, request, jsonify
from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de la app Flask
app = Flask(__name__)

# Cliente OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
assistant_id = os.getenv("ASSISTANT_ID", "asst_Q3M9vDA4aN89qQNH1tDXhjaE")
user_threads = {}

# Evento para manejar respuestas de OpenAI
class EventHandler(AssistantEventHandler):
    def __init__(self):
        super().__init__()
        self.assistant_message = ""

    @override
    def on_text_created(self, text) -> None:
        self.assistant_message += text.value

    @override
    def on_text_delta(self, delta, snapshot):
        self.assistant_message += delta.value

# Función para convertir texto a audio
def text_to_audio(text):
    tts = gTTS(text)
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(tmp_file.name)
    final_path = f"/tmp/{os.path.basename(tmp_file.name)}"
    shutil.move(tmp_file.name, final_path)
    return final_path

# Función para subir el archivo de audio a WhatsApp y obtener el media_id
def upload_audio_to_whatsapp(audio_file_path):
    url = f'https://graph.facebook.com/v21.0/{os.getenv("PHONE_NUMBER_ID")}/media'
    headers = {
        'Authorization': f'Bearer {os.getenv("ACCESS_TOKEN")}',
    }
    files = {
        'file': open(audio_file_path, 'rb'),
        'type': 'audio/mp3',
        'messaging_product': 'whatsapp'
    }
    
    response = requests.post(url, headers=headers, files=files)
    files['file'].close()
    
    if response.status_code == 200:
        media_id = response.json().get('id')
        return media_id
    else:
        logger.error(f"Error al subir archivo: {response.json()}")
        return None

# Función para enviar el mensaje con el archivo de audio a WhatsApp
def send_audio_message_to_whatsapp(media_id, recipient_id, text_message="Aquí está tu mensaje de audio"):
    url = f'https://graph.facebook.com/v14.0/{os.getenv("PHONE_NUMBER_ID")}/messages'
    headers = {
        'Authorization': f'Bearer {os.getenv("ACCESS_TOKEN")}',
        'Content-Type': 'application/json'
    }
    data = {
        'messaging_product': 'whatsapp',
        'to': recipient_id,
        'text': text_message,  # Añadir texto al mensaje de audio
        'type': 'audio',
        'audio': {'id': media_id}
    }
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        logger.info("Mensaje de audio enviado correctamente")
    else:
        logger.error(f"Error al enviar mensaje: {response.json()}")

# Ruta para generar respuesta y mandar audio
@app.route('/generate-response', methods=['POST'])
def generate_response():
    data = request.json
    user_message = data.get('message')
    user_id = data.get('sender_id')

    if not user_message or not user_id:
        return jsonify({'response': "No se proporcionó un mensaje o ID de usuario válido."}), 400

    try:
        # Si es el primer mensaje del usuario, crear un thread
        if user_id not in user_threads:
            thread = client.beta.threads.create()
            user_threads[user_id] = thread.id

        # Enviar el mensaje del usuario al modelo OpenAI
        client.beta.threads.messages.create(
            thread_id=user_threads[user_id],
            role="user",
            content=user_message
        )

        # Iniciar el evento y generar la respuesta
        event_handler = EventHandler()
        with client.beta.threads.runs.stream(
            thread_id=user_threads[user_id],
            assistant_id=assistant_id,
            event_handler=event_handler,
        ) as stream:
            stream.until_done()

        assistant_message = event_handler.assistant_message
        audio_file = text_to_audio(assistant_message)  # Convertir respuesta a audio

        # Subir el audio a WhatsApp y obtener el media_id
        media_id = upload_audio_to_whatsapp(audio_file)
        
        if media_id:
            # Enviar el mensaje de audio a WhatsApp
            send_audio_message_to_whatsapp(media_id, user_id, text_message=assistant_message)
            return jsonify({'response': assistant_message, 'audio_sent': True})
        else:
            return jsonify({'response': assistant_message, 'audio_sent': False})

    except Exception as e:
        return jsonify({'response': f"Error al generar respuesta: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
