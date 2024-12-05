import requests

# URL base de la API de Tokko
TOKKO_API_URL = "https://www.tokkobroker.com/api/v1/property/"
API_KEY = "34430fc661d5b961de6fd53a9382f7a232de3ef0"

def build_search_data(filters):
    """
    Construye los datos de búsqueda basados en los filtros proporcionados.
    """
    search_data = {
        "current_localization_id": filters.get("localization_id", 0),
        "current_localization_type": filters.get("localization_type", "country"),
        "price_from": filters.get("price_from", 0),
        "price_to": filters.get("price_to", 999999999),
        "operation_types": filters.get("operation_types", []),
        "property_types": filters.get("property_types", []),
        "currency": filters.get("currency", "ANY"),
        "filters": filters.get("additional_filters", []),
    }
    return search_data

def search_properties(filters):
    """
    Realiza la búsqueda de propiedades en la API de Tokko.
    """
    search_data = build_search_data(filters)
    
    # Verificar que al menos un tipo de operación esté definido
    if not search_data["operation_types"]:
        print("Error: No se definió ningún tipo de operación en los filtros.")
        return []

    # Verificar que la localización tenga datos válidos
    if search_data["current_localization_id"] == 0:
        print("Advertencia: No se especificó una localización válida. Usando predeterminada (país).")
    
    # Construir la URL con la clave de API
    url = f"{TOKKO_API_URL}search/?key={API_KEY}"

    # Realizar la solicitud a la API
    try:
        print("Enviando datos a la API:", search_data)
        response = requests.post(url, json=search_data)
        response.raise_for_status()  # Lanza excepción si hay error HTTP
        properties = response.json()
        print("Resultados obtenidos correctamente.")
        return properties
    except requests.exceptions.HTTPError as http_err:
        print(f"Error HTTP al conectarse a la API de Tokko: {http_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Error en la solicitud a la API de Tokko: {req_err}")
    except KeyError as key_err:
        print(f"Error al procesar los datos de la respuesta: {key_err}")
    return []

def show_results(filters, results):
    """
    Muestra los resultados en base a los filtros y los datos obtenidos.
    """
    operation_map = {1: "venta", 2: "alquiler", 3: "alquiler temporal"}
    
    # Manejar casos donde el filtro esté vacío
    if filters.get("operation_types"):
        operation_type = operation_map.get(filters["operation_types"][0], "operación desconocida")
    else:
        operation_type = "operación desconocida"

    print(f"Mostrando resultados para la operación: {operation_type}")
    for property in results.get("objects", []):
        print(f"Título: {property.get('publication_title', 'Sin título')}")
        print(f"Precio: {property.get('price', 'No disponible')}")
        print(f"Dirección: {property.get('fake_address', 'No especificada')}")
        print(f"Superficie total: {property.get('total_surface', 'No especificada')}")
        print("-" * 40)

# Ejemplo de uso
if __name__ == "__main__":
    # Filtros de ejemplo
    filtros = {
        "localization_id": 1234,  # ID de localización (ejemplo)
        "localization_type": "city",  # Tipo de localización
        "price_from": 100000,
        "price_to": 500000,
        "operation_types": [2],  # 1: Venta, 2: Alquiler, 3: Alquiler temporal
        "property_types": [3],  # 3: Casa
        "currency": "USD",
    }

    # Buscar propiedades
    resultados = search_properties(filtros)

    # Mostrar resultados
    if resultados:
        show_results(filtros, resultados)
    else:
        print("No se encontraron resultados.")
