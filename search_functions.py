import requests
import re

# URL base de la API de Tokko
TOKKO_API_URL = "https://www.tokkobroker.com/api/v1/property/"
API_KEY = "34430fc661d5b961de6fd53a9382f7a232de3ef0"

def extract_filters(user_message):
    """
    Extrae los filtros del mensaje del usuario.
    """
    filters = {
        "operation_types": [],  # Lista de operaciones: [1] Venta, [2] Alquiler
        "price_from": None,
        "price_to": None,
        "locations": [],
        "property_types": [],
    }

    # Identificar palabras clave para operación
    if "alquiler" in user_message.lower() or "alquilar" in user_message.lower():
        filters["operation_types"].append(2)  # Alquiler
    if "venta" in user_message.lower() or "comprar" in user_message.lower():
        filters["operation_types"].append(1)  # Venta

    # Si no se encuentra ninguna operación, buscar ambas
    if not filters["operation_types"]:
        filters["operation_types"] = [1, 2]

    # Extraer rango de precios usando expresiones regulares
    price_match = re.findall(r"precio.*?(\d+)", user_message.lower())
    if len(price_match) >= 2:
        filters["price_from"], filters["price_to"] = map(int, price_match[:2])
    elif len(price_match) == 1:
        filters["price_from"] = int(price_match[0])

    # Extraer posibles ubicaciones (ejemplo: "en Buenos Aires")
    location_match = re.findall(r"en ([\w\s]+)", user_message.lower())
    filters["locations"] = [loc.strip() for loc in location_match]

    return filters

def search_properties(filters):
    """
    Realiza la búsqueda de propiedades en la API de Tokko.
    """
    search_data = {
        "operation_types": filters["operation_types"],
        "price_from": filters["price_from"],
        "price_to": filters["price_to"],
    }

    # Construir la URL con la clave de API
    url = f"{TOKKO_API_URL}search/?key={API_KEY}"

    try:
        response = requests.post(url, json=search_data)
        response.raise_for_status()  # Lanza excepción si hay error HTTP
        properties = response.json()

        # Filtrar las propiedades con base en los filtros específicos
        filtered_properties = []
        for property in properties.get("objects", []):
            match_operation = any(
                op["operation_type"] in ["Rent", "Sale"] and op["operation_id"] in filters["operation_types"]
                for op in property.get("operations", [])
            )
            if not match_operation:
                continue

            # Filtrar por ubicación si se proporcionaron
            if filters["locations"]:
                location = property.get("fake_address", "").lower()
                if not any(loc.lower() in location for loc in filters["locations"]):
                    continue

            filtered_properties.append(property)

        return filtered_properties
    except requests.exceptions.RequestException as req_err:
        print(f"Error al solicitar propiedades: {req_err}")
        return []
