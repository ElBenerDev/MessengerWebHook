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
        logging.info(f"JSON generado para la búsqueda: {data_param}")  # Log de depuración
        params = {
            "key": API_KEY,
            "data": data_param,
            "format": "json",
            "limit": 20
        }
        response = requests.get(endpoint, params=params)
        logging.info(f"Solicitud enviada a la API de búsqueda: {response.url}")
        if response.status_code == 200:
            logging.info(f"Respuesta de la API: {response.text}")  # Log de la respuesta
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
    Función para interactuar con el usuario y preguntar los parámetros de búsqueda.
    """
    # Tipos de operación
    print("\nTipos de operación disponibles:")
    print("  1: Sale")
    print("  2: Rent")
    selected_operations = input("Seleccione los IDs de tipos de operación (separados por comas, o deje vacío para usar solo alquiler): ")
    if selected_operations:
        operation_ids = [int(op.strip()) for op in selected_operations.split(",") if op.strip().isdigit()]
    else:
        operation_ids = [2]  # Usar solo alquiler por defecto

    # Tipos de propiedad
    print("\nTipos de propiedad disponibles:")
    print("  7: Bussiness Premises")
    print("  13: Condo")
    print("  2: Apartment")
    print("  3: House")
    print("  10: Garage")
    print("  1: Land")
    print("  12: Industrial Ship")
    selected_properties = input("Seleccione los IDs de tipos de propiedad (separados por comas, o deje vacío para usar solo departamentos): ")
    if selected_properties:
        property_ids = [int(prop.strip()) for prop in selected_properties.split(",") if prop.strip().isdigit()]
    else:
        property_ids = [2]  # Usar solo departamentos por defecto

    # Obtener el tipo de cambio
    exchange_rate = get_exchange_rate()
    if not exchange_rate:
        print("No se pudo obtener el tipo de cambio. Intente nuevamente más tarde.")
        return None

    # Rango de precios
    print("\nIngrese los precios en USD. Se convertirán automáticamente a ARS para la búsqueda.")
    price_from = input("Ingrese el precio mínimo en USD (o deje vacío para omitir): ")
    price_to = input("Ingrese el precio máximo en USD (o deje vacío para omitir): ")

    # Procesar los valores de precio para eliminar comas, convertirlos a enteros y luego a ARS
    def process_price(price):
        try:
            return int(float(price.replace(",", "").strip()) * exchange_rate) if price else None
        except ValueError:
            print(f"El valor '{price}' no es un número válido. Ignorando este valor.")
            return None

    price_from = process_price(price_from)
    price_to = process_price(price_to)

    # Construir los parámetros de búsqueda
    search_params = {
        "operation_types": operation_ids,
        "property_types": property_ids,
        "price_from": price_from,
        "price_to": price_to,
        "currency": "ARS"  # La búsqueda se realiza en ARS
    }

    # Eliminar claves con valores None o listas vacías
    search_params = {k: v for k, v in search_params.items() if v is not None}

    logging.info(f"Parámetros de búsqueda: {search_params}")  # Log de los parámetros de búsqueda
    return search_params

def main():
    logging.info("Iniciando el programa.")

    # Paso 1: Preguntar al usuario los parámetros de búsqueda
    search_params = ask_user_for_parameters()
    if not search_params:
        return

    # Paso 2: Realizar la búsqueda con los parámetros seleccionados
    print("\nRealizando la búsqueda con los parámetros seleccionados...")
    search_results = fetch_search_results(search_params)

    if not search_results or 'objects' not in search_results or not search_results['objects']:
        print("No se pudieron obtener resultados desde la API de búsqueda.")
        return

    # Paso 3: Mostrar los resultados de la búsqueda
    print("\nResultados de la búsqueda:")
    for obj in search_results['objects']:
        # Filtrar solo los resultados de alquiler
        for operation in obj.get('operations', []):
            if operation['operation_id'] == 2:  # Asegurarse de que sea alquiler
                price = operation['prices'][0]['price']
                # Mostrar el precio mensual en ARS
                print(f"Ubicación: {obj['address']}")
                print(f"Precio: {price} ARS al mes")
                print(f"Descripción: {obj['description']}")
                print(f"Link: https://ficha.info/p/{obj['id']}")
                print("-----")

if __name__ == "__main__":
    main()