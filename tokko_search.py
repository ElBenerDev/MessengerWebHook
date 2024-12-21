import requests
import logging
import json

# Configuración de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s 1- %(levelname)s - %(message)s")

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

def search_with_user_budget(budget):
    """
    Realiza la búsqueda utilizando el presupuesto del usuario.
    """
    # Obtener el tipo de cambio
    exchange_rate = get_exchange_rate()
    if not exchange_rate:
        print("No se pudo obtener el tipo de cambio. Intente nuevamente más tarde.")
        return None

    # Parámetros de búsqueda utilizando el presupuesto
    search_params = {
        "operation_types": [2],  # Solo Rent
        "property_types": [2],   # Solo Apartment
        "price_from": 0 * exchange_rate,
        "price_to": budget * exchange_rate,  # Usamos el presupuesto del usuario
        "currency": "ARS"  # La búsqueda se realiza en ARS
    }

    # Realizar la búsqueda
    search_results = fetch_search_results(search_params)
    
    if search_results:
        return json.dumps(search_results, indent=4)
    else:
        return "No se encontraron resultados."

# Función que simula la interacción del asistente (por ejemplo, recibes el presupuesto del usuario)
def assistant_interaction():
    """
    Simula la interacción con el usuario donde se le pregunta su presupuesto.
    """
    # Supongamos que el presupuesto es recibido como 5000 USD
    user_budget = 5000  # Este presupuesto debe ser obtenido de la conversación

    print(f"\nGracias por la info. Déjame buscar opciones de departamentos dentro de tu presupuesto de {user_budget} USD. Un momento, por favor.")

    # Llamar a la función de búsqueda con el presupuesto proporcionado
    search_results = search_with_user_budget(user_budget)

    if search_results:
        print("\nResultados de la búsqueda:")
        print(search_results)
    else:
        print("\nNo se encontraron resultados dentro de ese presupuesto.")

# Ejecutar la función principal
if __name__ == "__main__":
    assistant_interaction()
