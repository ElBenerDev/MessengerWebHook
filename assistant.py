from flask import Flask, request, jsonify
from openai import OpenAI
import os
import time
from tokko_search import extract_filters, search_properties, format_property_response

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
assistant_id = os.getenv("ASSISTANT_ID", "asst_Q3M9vDA4aN89qQNH1tDXhjaE")

class ConversationManager:
    def __init__(self):
        self.threads = {}
        self.contexts = {}
        print("ConversationManager inicializado")

    def get_thread_id(self, user_id):
        if user_id not in self.threads:
            thread = client.beta.threads.create()
            self.threads[user_id] = thread.id
            self.contexts[user_id] = {
                'location': None,
                'property_type': None,
                'operation_type': None,
                'rooms': None,
                'budget': None,
                'last_search': None
            }
            print(f"Nuevo thread creado para usuario {user_id}: {thread.id}")
        return self.threads[user_id]

    def get_context(self, user_id):
        return self.contexts.get(user_id, {})

    def update_context(self, user_id, updates):
        if user_id not in self.contexts:
            self.contexts[user_id] = {}
        self.contexts[user_id].update(updates)

conversation_manager = ConversationManager()

def wait_for_run(thread_id, run_id, max_wait_seconds=30):
    start_time = time.time()
    while True:
        if time.time() - start_time > max_wait_seconds:
            return False

        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run_id
        )

        if run_status.status == 'completed':
            return True
        elif run_status.status == 'requires_action':
            # Manejar las acciones requeridas por el asistente
            if run_status.required_action.type == "submit_tool_outputs":
                tool_outputs = []
                for tool_call in run_status.required_action.submit_tool_outputs.tool_calls:
                    if tool_call.function.name == "search_properties":
                        # Realizar búsqueda de propiedades
                        context = conversation_manager.get_context(thread_id)
                        filters = extract_filters(context)
                        properties = search_properties(filters)
                        result = format_property_response(properties)
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": result
                        })

                # Enviar los resultados al asistente
                client.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread_id,
                    run_id=run_id,
                    tool_outputs=tool_outputs
                )
                continue

        elif run_status.status in ['failed', 'cancelled', 'expired']:
            return False

        time.sleep(1)

def generate_response_internal(message, user_id):
    if not message or not user_id:
        return {'response': "No se proporcionó un mensaje o un ID de usuario válido."}

    try:
        thread_id = conversation_manager.get_thread_id(user_id)
        context = conversation_manager.get_context(user_id)

        # Verificar y esperar cualquier ejecución pendiente
        runs = client.beta.threads.runs.list(thread_id=thread_id)
        for run in runs.data:
            if run.status not in ['completed', 'failed', 'cancelled', 'expired']:
                if not wait_for_run(thread_id, run.id):
                    return {'response': "Lo siento, hubo un error al procesar tu mensaje (timeout)."}

        # Crear el nuevo mensaje
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )

        # Ejecutar el asistente con las herramientas disponibles
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
            tools=[{
                "type": "function",
                "function": {
                    "name": "search_properties",
                    "description": "Busca propiedades según los criterios especificados",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "operation_type": {
                                "type": "string",
                                "enum": ["alquiler", "venta"]
                            },
                            "location": {
                                "type": "string"
                            },
                            "property_type": {
                                "type": "string",
                                "enum": ["departamento", "casa", "ph", "local"]
                            },
                            "rooms": {
                                "type": "integer",
                                "minimum": 1
                            }
                        }
                    }
                }
            }]
        )

        if not wait_for_run(thread_id, run.id):
            return {'response': "Lo siento, hubo un error al procesar tu mensaje (timeout)."}

        messages = client.beta.threads.messages.list(
            thread_id=thread_id
        )

        for message in messages.data:
            if message.role == "assistant":
                return {'response': message.content[0].text.value}

        return {'response': "No se pudo obtener una respuesta del asistente."}

    except Exception as e:
        print(f"Error en generate_response_internal: {str(e)}")
        return {'response': f"Error al generar respuesta: {str(e)}"}

@app.route('/generate-response', methods=['POST'])
def generate_response():
    try:
        data = request.json
        if not data or 'message' not in data or 'sender_id' not in data:
            return jsonify({'error': 'No message or sender_id provided'}), 400

        response_data = generate_response_internal(data['message'], data['sender_id'])
        return jsonify(response_data)

    except Exception as e:
        print(f"Error en generate_response: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode and token:
        if mode == 'subscribe' and token == os.getenv('FACEBOOK_VERIFY_TOKEN'):
            print("Webhook verificado!")
            return challenge
        else:
            return 'Forbidden', 403

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)