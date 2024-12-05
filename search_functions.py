import requests

# Función para procesar el mensaje del usuario y extraer filtros
def extract_filters(user_message):
    filters = {
        "price_from": 0,
        "price_to": 999999999,  # Rango amplio por defecto
        "operation_types": [],  # 1: Venta, 2: Alquiler, 3: Alquiler temporal
        "property_types": [],  # Tipos de propiedad
        "currency": "ANY",  # Moneda por defecto
        "current_localization_type": "country",  # Nivel de localización
        "current_localization_id": [0],  # ID de país (global por defecto)
        "filters": [],
        "with_tags": [],
        "without_tags": []
    }

    # Detectar intención de operación
    if "alquiler" in user_message.lower():
        filters["operation_types"] = [2]  # Alquiler
    elif "venta" in user_message.lower() or "comprar" in user_message.lower():
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

    return filters

# Función para realizar la búsqueda avanzada
def search_properties(filters):
    # URL del endpoint de búsqueda
    base_url = "https://www.tokkobroker.com/api/v1/property/search"
    api_key = "34430fc661d5b961de6fd53a9382f7a232de3ef0"
    tokko_url = f"{base_url}?key={api_key}"

    # Solicitud POST con los filtros
    try:
        response = requests.post(tokko_url, json=filters)
        response.raise_for_status()
        properties = response.json()

        # Procesar resultados
        results = []
        for property in properties.get("objects", []):
            results.append({
                "title": property.get("title", "Sin título"),
                "price": property.get("price", "No especificado"),
                "operation": "Venta" if property.get("operation_type") == 1 else "Alquiler",
                "location": property.get("location", {}).get("address", "Ubicación no disponible"),
                "description": property.get("description", "Sin descripción"),
            })
        return results

    except requests.exceptions.RequestException as e:
        print(f"Error al conectarse a la API de Tokko: {e}")
        return []

# Función para mostrar resultados al usuario
def show_results(filters, results):
    operation_map = {1: "venta", 2: "alquiler", 3: "alquiler temporal"}
    operation_type = operation_map.get(filters["operation_types"][0], "operación desconocida")
    
    print(f"Resultados para {operation_type}:")
    print(f"Rango de precios: {filters['price_from']} - {filters['price_to']} {filters['currency']}")
    print(f"Tipo de propiedad: {', '.join(str(pt) for pt in filters['property_types']) or 'cualquier tipo'}")
    print(f"Ubicación: {filters['current_localization_type']} ID {filters['current_localization_id'][0]}")

    if not results:
        print("No se encontraron propiedades que cumplan con estos criterios.")
    else:
        for property in results:
            print(f"\nTítulo: {property['title']}")
            print(f"Precio: {property['price']}")
            print(f"Operación: {property['operation']}")
            print(f"Ubicación: {property['location']}")
            print(f"Descripción: {property['description']}")

# Ejemplo de uso
mensaje_usuario = "Quiero alquilar un departamento de menos de 2000 dólares en Caballito"
filtros = extract_filters(mensaje_usuario)
resultados = search_properties(filtros)
show_results(filtros, resultados)
