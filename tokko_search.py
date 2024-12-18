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

# URL de la API de tipo de cambio (puedes usar otra fuente si prefieres)
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
            # Validar y limpiar los resultados
            cleaned_results = []
            for property in results.get("objects", []):
                try:
                    cleaned_results.append({
                        "title": property.get("title", "Sin título"),
                        "address": property.get("address", "Dirección no disponible"),
                        "price": property.get("price", "Precio no disponible"),
                        "surface": property.get("surface", "Superficie no especificada"),
                        "details": property.get("description", "Sin detalles"),
                        "image": property.get("image", "https://via.placeholder.com/150"),  # Imagen por defecto
                        "url": property.get("url", "#")  # Enlace por defecto
                    })
                except Exception as e:
                    logging.error(f"Error al procesar una propiedad: {str(e)}")
            return cleaned_results
        else:
            logging.error(f"Error al realizar la búsqueda. Código de estado: {response.status_code}")
            logging.error(f"Respuesta del servidor: {response.text}")
            return None
    except Exception as e:
        logging.exception("Error al conectarse a la API de búsqueda.")
        return None

def search_properties(params):
    """
    Realiza la búsqueda de propiedades con los parámetros proporcionados.
    """
    # Obtener el tipo de cambio
    exchange_rate = get_exchange_rate()
    if not exchange_rate:
        logging.error("No se pudo obtener el tipo de cambio. Intente nuevamente más tarde.")
        return {"error": "No se pudo obtener el tipo de cambio. Intente nuevamente más tarde."}

    # Convertir precios de USD a ARS si están presentes
    def process_price(price):
        try:
            return int(float(price) * exchange_rate) if price else None
        except ValueError:
            logging.error(f"El valor '{price}' no es un número válido.")
            return None

    # Procesar los precios en los parámetros
    if "price_from" in params:
        params["price_from"] = process_price(params["price_from"])
    if "price_to" in params:
        params["price_to"] = process_price(params["price_to"])

    # Realizar la búsqueda
    search_results = fetch_search_results(params)
    if not search_results:
        return {"error": "No se pudieron obtener resultados desde la API de búsqueda."}

    return search_results

def format_properties_message(properties):
    """
    Formatea los resultados de las propiedades en un mensaje legible.
    """
    if not properties:
        return "No se encontraron propiedades que coincidan con los criterios de búsqueda."

    message = "He encontrado algunas opciones que se ajustan a tus necesidades:\n\n"
    for i, property in enumerate(properties, start=1):
        message += f"{i}. **{property['title']}**\n"
        message += f"   - Dirección: {property['address']}\n"
        message += f"   - Precio: {property['price']}\n"
        message += f"   - Superficie: {property['surface']}\n"
        message += f"   - Detalles: {property['details']}\n"
        message += f"   - [Ver propiedad]({property['url']})\n"
        message += f"   ![Imagen]({property['image']})\n\n"
    return message