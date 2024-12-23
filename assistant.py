from flask import Flask, request, jsonify
from openai import OpenAI
import os
import logging
import requests
import json

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configura tu cliente con la API key desde el entorno
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ID del asistente
assistant_id = os.getenv("ASSISTANT_ID", "asst_Q3M9vDA4aN89qQNH1tDXhjaE")

# Estado de la conversación
user_states = {}

# Parámetros de búsqueda iniciales
search_params = {
    "operation_types": [1],  # Solo Renta por defecto
    "property_types": [2],    # Solo Departamento por defecto
    "price_from": 0,
    "price_to": 5000000,
    "currency": "ARS"
}

@app.route('/generate-response', methods=['POST'])
def generate_response():
    data = request.json
    user_message = data.get('message')
    user_id = data.get('sender_id')

    if not user_message or not user_id:
        return jsonify({'response': "No se proporcionó un mensaje o ID de usuario válido."}), 400

    logger.info(f"Mensaje recibido del usuario {user_id}: {user_message}")

    # Inicializar el estado del usuario si no existe
    if user_id not in user_states:
        user_states[user_id] = {
            "search_params": search_params.copy(),
            "step": 0  # Controla el paso de la conversación
        }

    user_state = user_states[user_id]

    # Lógica de conversación
    if user_state["step"] == 0:
        # Preguntar por el tipo de operación
        response_message = "¿Estás buscando una **renta** o una **venta**? Responde con 'renta' o 'venta'."
        user_state["step"] = 1

    elif user_state["step"] == 1:
        # Procesar la respuesta sobre el tipo de operación
        if "renta" in user_message.lower():
            user_state["search_params"]["operation_types"] = [1]  # Renta
            response_message = "Perfecto, ¿qué tipo de propiedad estás buscando? (casa, departamento, etc.)"
            user_state["step"] = 2
        elif "venta" in user_message.lower():
            user_state["search_params"]["operation_types"] = [2]  # Venta
            response_message = "Perfecto, ¿qué tipo de propiedad estás buscando? (casa, departamento, etc.)"
            user_state["step"] = 2
        else:
            response_message = "Por favor, responde con 'renta' o 'venta'."

    elif user_state["step"] == 2:
        # Procesar la respuesta sobre el tipo de propiedad
        property_type = user_message.lower()
        if property_type == "casa":
            user_state["search_params"]["property_types"] = [1]  # Casa
            response_message = "¿Cuál es tu rango de precios? Por favor, indícame el precio mínimo y máximo (ejemplo: 1000000-5000000)."
            user_state["step"] = 3
        elif property_type == "departamento":
            user_state["search_params"]["property_types"] = [2]  # Departamento
            response_message = "¿Cuál es tu rango de precios? Por favor, indícame el precio mínimo y máximo (ejemplo: 1000000-5000000)."
            user_state["step"] = 3
        else:
            response_message = "No reconozco ese tipo de propiedad. ¿Buscas una casa o un departamento?"

    elif user_state["step"] == 3:
        # Procesar el rango de precios
        try:
            price_from, price_to = map(int, user_message.split('-'))
            user_state["search_params"]["price_from"] = price_from
            user_state["search_params"]["price_to"] = price_to
            response_message = "Gracias por la información. Ahora procederé a buscar propiedades."
            user_state["step"] = 4
        except ValueError:
            response_message = "Por favor, proporciona un rango de precios válido en el formato: mínimo-máximo."

    elif user_state["step"] == 4:
        # Realizar la búsqueda
        search_results = fetch_search_results(user_state["search_params"])
        if not search_results:
            return jsonify({'response': "No se pudieron obtener resultados desde la API de búsqueda."}), 500

        # Enviar resultados uno por uno
        response_message = "Aquí están los resultados de la búsqueda:"
        for property in search_results.get('properties', []):
            property_message = f"\n- **Tipo de propiedad:** {property.get('property_type')}\n" \
                               f"- **Ubicación:** {property.get('location')}\n" \
                               f"- **Precio:** {property.get('price')} ARS\n" \
                               f"- **Habitaciones:** {property.get('rooms')}\n" \
                               f"- **Detalles:** {property.get('details')}\n" \
                               f"[Ver más detalles]({property.get('url')})"
            response_message += property_message

        # Limpiar datos del usuario después de la búsqueda
        del user_states[user_id]

    # Enviar la respuesta al usuario
    return jsonify({'response': response_message})

def fetch_search_results(search_params):
    endpoint = "https://www.tokkobroker.com/api/v1/property/search/"
    try:
        data_param = json.dumps(search_params, separators=(',', ':'))  # Elimina espacios adicionales
        params = {
            "key": os.getenv("PROPERTY_API_KEY"),  # Asegúrate de tener esta clave en tus variables de entorno
            "data": data_param,
            "format": "json",
            "limit": 20
        }
        response = requests.get(endpoint, params=params)
        logger.info(f"Solicitud enviada a la API de búsqueda: {response.url}")
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error al realizar la búsqueda. Código de estado: {response.status_code}")
            return None
    except Exception as e:
        logger.exception("Error al conectarse a la API de búsqueda.")
        return None

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)