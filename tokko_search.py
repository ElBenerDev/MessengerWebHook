import requests
import logging
import json

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Clave de la API de propiedades
API_KEY = "34430fc661d5b961de6fd53a9382f7a232de3ef0"

# URL de la API de tipo de cambio
EXCHANGE_RATE_API_URL = "https://api.exchangerate-api.com/v4/latest/USD"

def get_exchange_rate():
    """
    Obtiene el tipo de cambio actual de USD a ARS.
    """
    try:
        response = requests.get(EXCHANGE_RATE_API_URL)
        if response.status_code == 200:
            data = response.json()
            return data["rates"]["ARS"]  # Tipo de cambio de USD a ARS
        else:
            logging.error(f"Error al obtener el tipo de cambio. Código de estado: {response.status_code}")
            return None
    except Exception as e:
        logging.exception("Error al conectarse a la API de tipo de cambio.")
        return None

def fetch_search_results(search_params):
    """
    Función para realizar la búsqueda en la API con los parámetros seleccionados.
    """
    endpoint = "https://www.tokkobroker.com/api/v1/property/search/"
    try:
        # Convertir los parámetros a JSON
        data_param = json.dumps(search_params, separators=(',', ':'))  # Elimina espacios adicionales
        logging.info(f"JSON generado para la búsqueda: {data_param}")
        params = {
            "key": API_KEY,
            "data": data_param,
            "format": "json",
            "limit": 20
        }
        response = requests.get(endpoint, params=params)
        logging.info(f"Solicitud enviada a la API de búsqueda: {response.url}")
        if response.status_code == 200:
            results = response.json()
            logging.info(f"Resultados de búsqueda recibidos: {results}")
            return results  # Devolver directamente los resultados
        else:
            logging.error(f"Error al realizar la búsqueda. Código de estado: {response.status_code}")
            logging.error(f"Respuesta del servidor: {response.text}")
            return None
    except Exception as e:
        logging.exception("Error al conectarse a la API de búsqueda.")
        return None

def format_properties_message(properties):
    """
    Formatea los resultados de las propiedades en un mensaje legible.
    """
    if not properties or not properties.get("objects"):
        return "No se encontraron propiedades que coincidan con los criterios de búsqueda."

    message = "He encontrado algunas opciones que se ajustan a tus necesidades:\n\n"
    for i, property in enumerate(properties.get("objects", []), start=1):
        title = property.get('title', 'Sin título')
        address = property.get('address', 'Dirección no disponible')
        price_info = property.get('operations', [{}])[0].get('prices', [{}])[0]
        price = price_info.get('price', 'Precio no disponible')
        currency = price_info.get('currency', 'ARS')
        image_url = property.get('photos', [{}])[0].get('image', 'https://via.placeholder.com/150')  # Usar la primera imagen
        description = property.get('description', 'Descripción no disponible').strip().replace('\n', ' ')  # Limpiar la descripción

        # Formatear el mensaje de manera más clara
        message += f"{i}. **{title}**\n"
        message += f"   - Ubicación: {address}\n"
        message += f"   - Precio: {price} {currency}\n"
        message += f"   - Descripción: {description}\n"
        message += f"   - [Detalles y fotos aquí](https://icha.info/pebxTxQQZ)\n"  # Cambia esto por la URL real si está disponible
        message += f"   ![Imagen]({image_url})\n\n"

    message += "Si estás interesado en alguna de estas propiedades o tienes otra consulta, no dudes en decírmelo. ¡Estoy aquí para ayudar! 😊"
    return message

def search_properties(params):
    """
    Realiza la búsqueda de propiedades con los parámetros proporcionados.
    """
    # Obtener el tipo de cambio
    exchange_rate = get_exchange_rate()
    if not exchange_rate:
        logging.error("No se pudo obtener el tipo de cambio. Intente nuevamente más tarde.")
        return {"error": "No se pudo obtener el tipo de cambio. Intente nuevamente más tarde."}

    # Realizar la búsqueda
    search_results = fetch_search_results(params)
    if not search_results:
        return {"error": "No se pudieron obtener resultados desde la API de búsqueda."}

    # Convertir precios de USD a ARS si están presentes
    def process_price(price):
        try:
            return int(float(price) * exchange_rate) if price else None
        except ValueError:
            logging.error(f"El valor '{price}' no es un número válido.")
            return None

    # Procesar los precios en los resultados
    for property in search_results.get("objects", []):
        if "price" in property:
            property["price"] = process_price(property["price"])

    logging.info(f"Resultados de búsqueda procesados: {search_results}")
    return search_results