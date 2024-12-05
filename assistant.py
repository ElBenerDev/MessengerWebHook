from flask import Flask, request, jsonify
from openai import OpenAI
from openai import AssistantEventHandler
import os
from search_functions import extract_filters, search_properties

app = Flask(__name__)

# Configura tu cliente con la API key desde el entorno
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

assistant_id = os.getenv("ASSISTANT_ID", "asst_Q3M9vDA4aN89qQNH1tDXhjaE")

# Variable global para almacenar el thread_id activo
active_thread_id = None

class EventHandler(AssistantEventHandler):
    def __init__(self):
        super().__init__()
        self.assistant_message = ""

    def on_text_created(self, text) -> None:
        print(f"Asistente: {text.value}", end="", flush=True)
        self.assistant_message += text.value

@app.route('/generate-response', methods=['POST'])
def generate_response():
    global active_thread_id

    data = request.json
    user_message = data.get('message')

    if not user_message:
        return jsonify({'response': "No se proporcionó un mensaje válido."}), 400

    if "buscar propiedades" in user_message.lower():
        filters = extract_filters(user_message)
        properties = search_properties(filters)

        if not properties:
            return jsonify({'response': "No se encontraron propiedades que coincidan con la búsqueda."}), 404

        response_message = "Propiedades encontradas:\n"
        for property in properties:
            title = property.get("title", "Sin título")
            description = property.get("description", "Sin descripción")
            location = property.get("fake_address", "Sin ubicación")
            operation = "Alquiler" if "Rent" in [op["operation_type"] for op in property["operations"]] else "Venta"
            price = next(
                (op["prices"][0]["price"] for op in property["operations"] if op["operation_type"] in ["Rent", "Sale"]),
                "No disponible"
            )

            response_message += (
                f"- **{title}**\n"
                f"  Operación: {operation}\n"
                f"  Precio: {price}\n"
                f"  Ubicación: {location}\n"
                f"  Descripción: {description}\n\n"
            )

        return jsonify({'response': response_message})

    return jsonify({'response': "Comando no reconocido."}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
