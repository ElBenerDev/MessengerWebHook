from flask import Flask, request, jsonify
from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import os
import requests  # Para realizar solicitudes HTTP

app = Flask(__name__)

# Configura tu cliente con la API key desde el entorno
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ID del asistente (debe configurarse como variable de entorno o directamente aquí)
assistant_id = os.getenv("ASSISTANT_ID", "asst_Q3M9vDA4aN89qQNH1tDXhjaE")  # Cambia esto si es necesario

# Crear un manejador de eventos para manejar el stream de respuestas del asistente
class EventHandler(AssistantEventHandler):
    def __init__(self):
        super().__init__()  # Inicializar correctamente la clase base
        self.assistant_message = ""  # Almacena el mensaje generado por el asistente

    @override
    def on_text_created(self, text) -> None:
        # Este evento se dispara cuando se crea texto en el flujo
        print(f"Asistente: {text.value}", end="", flush=True)
        self.assistant_message += text.value  # Agregar el texto al mensaje final

    @override
    def on_text_delta(self, delta, snapshot):
        # Este evento se dispara cuando el texto cambia o se agrega en el flujo
        print(delta.value, end="", flush=True)
        self.assistant_message += delta.value  # Agregar el texto al mensaje final

# Función para procesar el mensaje del usuario y extraer filtros
def extract_filters(user_message):
    # Filtros predeterminados
    filters = {
        "price_from": 0,
        "price_to": 1000000,  # Rango de precios predeterminado
        "operation_types": [],  # 1: Venta, 2: Alquiler, 3: Alquiler temporal
        "property_types": [],  # Tipos de propiedad (ejemplo: 2: Departamento)
        "currency": "USD",  # Moneda predeterminada
        "current_localization_id": None,  # Ubicación
        "current_localization_type": None,  # Tipo de ubicación (país, estado, división)
    }

    # Detectar intención (venta, alquiler, compra)
    if "alquiler" in user_message.lower():
        filters["operation_types"] = [2]  # Alquiler
    elif "comprar" in user_message.lower() or "venta" in user_message.lower():
        filters["operation_types"] = [1]  # Venta
    elif "alquiler temporal" in user_message.lower():
        filters["operation_types"] = [3]  # Alquiler temporal

    # Detectar rango de precios
    if "menos de" in user_message.lower():
        try:
            price_to = int(user_message.split("menos de")[1].split()[0].replace(",", "").replace(".", ""))
            filters["price_to"] = price_to
        except ValueError:
            pass

    if "más de" in user_message.lower():
        try:
            price_from = int(user_message.split("más de")[1].split()[0].replace(",", "").replace(".", ""))
            filters["price_from"] = price_from
        except ValueError:
            pass

    # Detectar tipo de propiedad
    if "departamento" in user_message.lower():
        filters["property_types"].append(2)  # Departamento
    if "casa" in user_message.lower():
        filters["property_types"].append(3)  # Casa
    if "oficina" in user_message.lower():
        filters["property_types"].append(5)  # Oficina

    # Detectar ubicación (ejemplo: "en Palermo")
    if "en " in user_message.lower():
        location = user_message.lower().split("en ")[1].split()[0]
        filters["current_localization_id"] = location  # Aquí podrías usar un mapeo de ubicaciones
        filters["current_localization_type"] = "division"  # Ejemplo: división

    return filters

# Función para realizar la búsqueda avanzada de propiedades en la API de Tokko
def search_properties(filters):
    # URL base del endpoint de búsqueda
    tokko_url = "https://www.tokkobroker.com/api/v1/property/search?key=34430fc661d5b961de6fd53a9382f7a232de3ef0"

    try:
        # Realizar la solicitud POST a la API de Tokko con los filtros
        response = requests.post(tokko_url, json=filters)
        response.raise_for_status()  # Lanza una excepción si la respuesta tiene un error HTTP

        # Procesar la respuesta JSON
        properties = response.json()
        results = []

        # Extraer información relevante de las propiedades
        for property in properties.get('objects', []):
            results.append({
                'title': property.get('title', 'Sin título'),
                'price': property.get('price', 'No especificado'),
                'location': property.get('location', {}).get('address', 'Ubicación no disponible'),
                'description': property.get('description', 'Sin descripción'),
            })

        return results

    except requests.exceptions.RequestException as e:
        # Manejar errores de conexión o respuesta
        print(f"Error al conectarse a la API de Tokko: {e}")
        return None

@app.route('/generate-response', methods=['POST'])
def generate_response():
    data = request.json
    user_message = data.get('message')

    if not user_message:
        return jsonify({'response': "No se proporcionó un mensaje válido."}), 400

    # Verificar si el mensaje solicita una búsqueda de propiedades
    if "buscar propiedades" in user_message.lower():
        # Extraer filtros del mensaje del usuario
        filters = extract_filters(user_message)

        # Realizar la búsqueda de propiedades
        properties = search_properties(filters)

        if properties is None:
            return jsonify({'response': "No se pudo realizar la búsqueda de propiedades en este momento."}), 500

        # Formatear los resultados para enviarlos al usuario
        response_message = "Aquí tienes algunas propiedades disponibles:\n"
        for property in properties:
            response_message += f"- **{property['title']}**\n"
            response_message += f"  Precio: {property['price']}\n"
            response_message += f"  Ubicación: {property['location']}\n"
            response_message += f"  Descripción: {property['description']}\n\n"

        return jsonify({'response': response_message})

    try:
        # Crear un nuevo hilo de conversación
        thread = client.beta.threads.create()
        print("Hilo creado:", thread)

        # Verificar que el hilo se creó correctamente
        if not thread or not hasattr(thread, "id"):
            raise ValueError("No se pudo crear el hilo de conversación.")

        # Enviar el mensaje del usuario al hilo
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_message
        )

        # Crear y manejar la respuesta del asistente
        event_handler = EventHandler()  # Instancia del manejador de eventos
        with client.beta.threads.runs.stream(
            thread_id=thread.id,
            assistant_id=assistant_id,
            event_handler=event_handler,
        ) as stream:
            stream.until_done()  # Esperar a que el flujo termine

        # Obtener el mensaje generado por el asistente
        assistant_message = event_handler.assistant_message

    except Exception as e:
        # Capturar cualquier error y devolverlo como respuesta
        return jsonify({'response': f"Error al generar respuesta: {str(e)}"}), 500

    return jsonify({'response': assistant_message})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)