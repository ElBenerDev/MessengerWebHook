from flask import Flask, request, jsonify
from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override

app = Flask(__name__)

# Configura tu cliente con la API key
client = OpenAI(api_key="tu_openai_api_key")
assistant_id = "asst_Q3M9vDA4aN89qQNH1tDXhjaE"

# Crear un manejador de eventos para manejar el stream de respuestas del asistente
class EventHandler(AssistantEventHandler):
    def __init__(self):
        self.response_text = ""

    @override
    def on_text_created(self, text) -> None:
        self.response_text += text.value

    @override
    def on_text_delta(self, delta, snapshot):
        self.response_text += delta.value

# Ruta para procesar mensajes
@app.route('/process_message', methods=['POST'])
def process_message():
    data = request.json
    user_message = data.get("message", "")
    thread_id = data.get("thread_id", None)

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    # Crear nuevo hilo si no existe
    if not thread_id:
        thread = client.beta.threads.create()
        thread_id = thread.id

    # Enviar mensaje del usuario al hilo
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_message
    )

    # Crear y manejar la respuesta del asistente
    handler = EventHandler()
    with client.beta.threads.runs.stream(
        thread_id=thread_id,
        assistant_id=assistant_id,
        event_handler=handler,
    ) as stream:
        stream.until_done()

    # Retornar respuesta
    return jsonify({
        "response": handler.response_text,
        "thread_id": thread_id
    })

if __name__ == '__main__':
    app.run(port=5000, debug=True)
