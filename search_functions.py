import requests

# URL base de la API de Tokko
TOKKO_API_URL = "https://www.tokkobroker.com/api/v1/property/"
API_KEY = "34430fc661d5b961de6fd53a9382f7a232de3ef0"

def extract_filters(user_message):
    """
    Función para extraer los filtros del mensaje del usuario.
    """
    filters = {
        "price_from": 0,
        "price_to": 999999999,
        "operation_types": [],
        "property_types": [],
        "currency": "ANY",
        "additional_filters": []
    }
    
    # Si el mensaje menciona 'comprar' o 'alquilar', establecer el tipo de operación
    if "alquilar" in user_message.lower():
        filters["operation_types"].append(2)  # 2: Alquiler
    elif "comprar" in user_message.lower():
        filters["operation_types"].append(1)  # 1: Venta
    
    # Buscar precios en el mensaje
    if "precio desde" in user_message.lower():
        filters["price_from"] = 100000  # Solo un ejemplo, deberías extraer el precio real
    
    if "precio hasta" in user_message.lower():
        filters["price_to"] = 500000  # Solo un ejemplo, deberías extraer el precio real
    
    return filters

def search_properties(filters):
    """
    Realiza la búsqueda de propiedades en la API de Tokko.
    """
    search_data = {
        "operation_types": filters["operation_types"],
        "price_from": filters["price_from"],
        "price_to": filters["price_to"],
        "currency": filters["currency"],
    }
    
    # Construir la URL con la clave de API
    url = f"{TOKKO_API_URL}search/?key={API_KEY}"

    try:
        print("Enviando datos a la API:", search_data)
        response = requests.post(url, json=search_data)
        response.raise_for_status()  # Lanza excepción si hay error HTTP
        properties = response.json()
        print("Resultados obtenidos correctamente.")
        return properties.get("objects", [])
    except requests.exceptions.RequestException as req_err:
        print(f"Error en la solicitud a la API de Tokko: {req_err}")
        return []
