from flask import Flask, request, jsonify
import os
import logging
import requests
import json
import time

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Función para obtener el tipo de cambio
def get_exchange_rate():
    EXCHANGE_RATE_API_URL = "https://api.exchangerate-api.com/v4/latest/USD"
    try:
        response = requests.get(EXCHANGE_RATE_API_URL)
        if response.status_code == 200:
            data = response.json()
            return data["rates"]["ARS"]  # Tipo de cambio de USD a ARS
        else:
            logger.error(f"Error al obtener el tipo de cambio. Código de estado: {response.status_code}")
            return None
    except Exception as e:
        logger.exception("Error al conectarse a la API de tipo de cambio.")
        return None

# Función para realizar la búsqueda de propiedades
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

# Almacenar datos de la conversación
user_data = {}

@app.route('/generate-response', methods=['POST'])
def generate_response():
    data = request.json
    user_message = data.get('message')
    user_id = data.get('sender_id')

    if not user_message or not user_id:
        return jsonify({'response': "No se proporcionó un mensaje o ID de usuario válido."}), 400

    logger.info(f"Mensaje recibido del usuario {user_id}: {user_message}")

    # Inicializar datos del usuario si no existe
    if user_id not in user_data:
        user_data[user_id] = {
            "conversation": []  # Para almacenar la conversación
        }

    # Agregar el mensaje del usuario a la conversación
    user_data[user_id]["conversation"].append(user_message)

    # Mantener la conversación
    response_message = "Gracias por tu mensaje. Estoy aquí para ayudarte. ¿Hay algo más que te gustaría saber antes de que busque propiedades?"

    # Si el usuario dice que no necesita más información, ejecutar la búsqueda
    if "no" in user_message.lower() or "nada más" in user_message.lower():
        response_message = "Entendido, buscaré propiedades ahora."

        # Ejecutar la búsqueda con parámetros predeterminados
        operation_ids = [2]  # Solo Rent
        property_ids = [2]   # Solo Apartment

        # Obtener el tipo de cambio
        exchange_rate = get_exchange_rate()
        if not exchange_rate:
            return jsonify({'response': "No se pudo obtener el tipo de cambio."}), 500

        # Rango de precios predeterminado (en USD convertido a ARS)
        price_from = int(0 * exchange_rate)
        price_to = int(500 * exchange_rate)

        # Construir los parámetros de búsqueda
        search_params = {
            "operation_types": operation_ids,
            "property_types": property_ids,
            "price_from": price_from,
            "price_to": price_to,
            "currency": "ARS"  # La búsqueda se realiza en ARS
        }

        # Realizar la búsqueda con los parámetros seleccionados
        logger.info("Realizando la búsqueda con los parámetros predeterminados...")
        search_results = fetch_search_results(search_params)

        if not search_results:
            return jsonify({'response': "No se pudieron obtener resultados desde la API de búsqueda."}), 500

        # Enviar resultados uno por uno
        response_message += "\nAquí están los resultados de la búsqueda:"
        for property in search_results.get('properties', []):
            property_message = f"\n- **Tipo de propiedad:** {property.get('property_type')}\n" \
                               f"- **Ubicación:** {property.get('location')}\n" \
                               f"- **Precio:** {property.get('price')} ARS\n" \
                               f"- **Habitaciones:** {property.get('rooms')}\n" \
                               f"- **Detalles:** {property.get('details')}\n" \
                               f"[Ver más detalles]({property.get('url')})"
            response_message += property_message
            time.sleep(1)  # Esperar un segundo entre mensajes (opcional)

        # Limpiar datos del usuario después de la búsqueda
        del user_data[user_id]

    logger.info(f"Mensaje generado por el asistente: {response_message}")
    return jsonify({'response': response_message})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)