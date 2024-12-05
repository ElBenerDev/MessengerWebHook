from flask import Flask, request, jsonify
from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import os

app = Flask(__name__)

# Configura tu cliente con la API key desde el entorno
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Crear un asistente y un hilo de conversación
assistant_id = "asst_Q3M9vDA4aN89qQNH1tDXhjaE"
thread = client.beta.threads.create()

class EventHandler(AssistantEventHandler):
    def __init__(self):
        self.response_text = ""

    @override
    def on_text_created(self, text) -> None:
        self.response_text += text.value

    @override
    def on_text_delta(self, delta, snapshot):
        self.response_text += delta.value

@app.route('/generate-response', methods=['POST'])
def generate_response():
    data = request.json
    user_message = data.get('message')

    # Enviar mensaje del usuario al hilo
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_message
    )

    # Crear y manejar la respuesta del asistente
    event_handler = EventHandler()
    with client.beta.threads.runs.stream(
        thread_id=thread.id,
        assistant_id=assistant_id,
        event_handler=event_handler,
    ) as stream:
        stream.until_done()

    return jsonify({'response': event_handler.response_text})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)