import requests

def extract_filters(user_message):
    filters = {
        "price_from": 0,
        "price_to": 1000000,
        "operation_types": [],
        "property_types": [],
        "currency": "USD",
        "location": None,
        "status": 2,  # Solo propiedades activas
        "deleted_at": None  # Solo propiedades no eliminadas
    }

    message = user_message.lower()

    # Tipo de operación
    if "alquiler temporal" in message:
        filters["operation_types"] = [3]
    elif "alquiler" in message:
        filters["operation_types"] = [2]
    elif "comprar" in message or "venta" in message:
        filters["operation_types"] = [1]

    # Rango de precios
    if "menos de" in message:
        try:
            price_to = int(''.join(filter(str.isdigit, message.split("menos de")[1].split()[0])))
            filters["price_to"] = price_to
        except (ValueError, IndexError):
            pass

    if "más de" in message:
        try:
            price_from = int(''.join(filter(str.isdigit, message.split("más de")[1].split()[0])))
            filters["price_from"] = price_from
        except (ValueError, IndexError):
            pass

    # Tipo de propiedad
    if "departamento" in message:
        filters["property_types"].append(2)
    if "casa" in message:
        filters["property_types"].append(3)
    if "ph" in message:
        filters["property_types"].append(13)
    if "oficina" in message:
        filters["property_types"].append(5)
    if "local" in message:
        filters["property_types"].append(4)

    # Ubicación
    location_indicators = ["en", "zona", "barrio", "cerca de"]
    for indicator in location_indicators:
        if indicator in message:
            try:
                location = message.split(indicator)[1].strip().split()[0]
                filters["location"] = location
                break
            except IndexError:
                continue

    return filters

def search_properties(filters):
    tokko_url = "https://www.tokkobroker.com/api/v1/property/search?key=34430fc661d5b961de6fd53a9382f7a232de3ef0"

    try:
        response = requests.post(tokko_url, json=filters)
        response.raise_for_status()

        properties = response.json()
        results = []

        for property in properties.get('objects', []):
            # Verificar si la propiedad está activa y no eliminada
            if property.get('deleted_at') or property.get('status') != 2:
                continue

            # Verificar el tipo de operación
            operations = property.get('operations', [])
            valid_operation = False
            operation_price = None
            operation_type = None

            for operation in operations:
                if filters['operation_types']:
                    if operation['operation_id'] in filters['operation_types']:
                        valid_operation = True
                        operation_type = operation['operation_type']
                        operation_price = next((price for price in operation['prices']), None)
                        break
                else:
                    valid_operation = True
                    operation_type = operation['operation_type']
                    operation_price = next((price for price in operation['prices']), None)
                    break

            if not valid_operation:
                continue

            # Crear objeto de propiedad con información detallada
            property_info = {
                'title': property.get('publication_title', 'Sin título'),
                'price': f"{operation_price['currency']} {operation_price['price']}" if operation_price else 'Precio no especificado',
                'location': property.get('fake_address', property.get('address', 'Ubicación no disponible')),
                'description': property.get('description', 'Sin descripción'),
                'surface': f"{property.get('total_surface', '0')} {property.get('surface_measurement', 'm²')}",
                'rooms': property.get('room_amount', 0),
                'bathrooms': property.get('bathroom_amount', 0),
                'property_type': property.get('type', {}).get('name', 'No especificado'),
                'operation_type': operation_type or 'No especificado',
                'expenses': property.get('expenses', 0),
                'reference_code': property.get('reference_code', ''),
                'images': [photo.get('image') for photo in property.get('photos', [])[:3]]  # Primeras 3 imágenes
            }

            results.append(property_info)

        return results

    except requests.exceptions.RequestException as e:
        print(f"Error al conectarse a la API de Tokko: {e}")
        return None