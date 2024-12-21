import requests
import logging
import json

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s 1- %(levelname)s - %(message)s"
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
        print(f"JSON generado para la búsqueda: {data_param}")  # Depuración
        params = {
            "key": API_KEY,
            "data": data_param,
            "format": "json",
            "limit": 20
        }
        response = requests.get(endpoint, params=params)
        logging.info(f"Solicitud enviada a la API de búsqueda: {response.url}")
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"Error al realizar la búsqueda. Código de estado: {response.status_code}")
            logging.error(f"Respuesta del servidor: {response.text}")
            return None
    except Exception as e:
        logging.exception("Error al conectarse a la API de búsqueda.")
        return None

def ask_user_for_parameters():
    """
    Genera parámetros de búsqueda predeterminados sin interacción del usuario.
    """
    # Parámetros predeterminados
    operation_ids = [2]  # Solo Rent
    property_ids = [2]   # Solo Apartment

    # Obtener el tipo de cambio
    exchange_rate = get_exchange_rate()
    if not exchange_rate:
        print("No se pudo obtener el tipo de cambio. Intente nuevamente más tarde.")
        return None

    # Rango de precios predeterminados (en USD convertido a ARS)
    price_from = int(0 * exchange_rate)
    price_to = int(10000 * exchange_rate)

    # Construir los parámetros de búsqueda
    search_params = {
        "operation_types": operation_ids,
        "property_types": property_ids,
        "price_from": price_from,
        "price_to": price_to,
        "currency": "ARS"  # La búsqueda se realiza en ARS
    }

    return search_params

def main():
    logging.info("Iniciando el programa.")

    # Paso 1: Generar parámetros de búsqueda predeterminados
    search_params = ask_user_for_parameters()
    if not search_params:
        return

    # Paso 2: Realizar la búsqueda con los parámetros seleccionados
    print("\nRealizando la búsqueda con los parámetros seleccionados...")
    search_results = fetch_search_results(search_params)

    if not search_results:
        print("No se pudieron obtener resultados desde la API de búsqueda.")
        return

    # Paso 3: Mostrar los resultados
    print("\nResultados de la búsqueda:")
    if 'objects' in search_results:
        for idx, prop in enumerate(search_results['objects']):
            print(f"\nPropiedad #{idx + 1}:")
            print(f"Dirección: {prop.get('address', 'No disponible')}")
            print(f"Precio: {prop['operations'][0]['prices'][0]['price']} ARS")
            print(f"Descripción: {prop.get('description', 'No disponible')}")
            print(f"Teléfono: {prop['branch']['phone']}")
            print(f"Fotos: {', '.join([photo['image'] for photo in prop.get('photos', [])])}")
    else:
        print("No se encontraron propiedades.")

if __name__ == "__main__":
    main()
