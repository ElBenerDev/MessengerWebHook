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
        "limit": 20,
        "offset": 0
    }

    message = user_message.lower()

    # Tipo de operación
    if "alquiler temporal" in message:
        filters["operation_types"] = [3]
    elif "alquiler" in message:
        filters["operation_types"] = [2]
    elif "comprar" in message or "venta" in message:
        filters["operation_types"] = [1]

    # Tipo de propiedad
    if "departamento" in message:
        filters["property_types"].append(2)  # Apartment
    if "casa" in message:
        filters["property_types"].append(3)  # House
    if "ph" in message:
        filters["property_types"].append(13)  # Condo
    if "oficina" in message:
        filters["property_types"].append(5)  # Office
    if "local" in message:
        filters["property_types"].append(7)  # Business Premises

    # Ubicación
    location_keywords = ["ballester", "villa ballester", "v.ballester", "v. ballester"]
    for keyword in location_keywords:
        if keyword in message:
            filters["location"] = "Villa Ballester"
            break

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

    print(f"Filtros generados: {filters}")
    return filters

def search_properties(filters):
    tokko_url = "https://www.tokkobroker.com/api/v1/property/search?key=34430fc661d5b961de6fd53a9382f7a232de3ef0"

    try:
        response = requests.post(tokko_url, json=filters)
        response.raise_for_status()
        data = response.json()

        if 'objects' not in data:
            print("No se encontraron objetos en la respuesta:", data)
            return []

        results = []
        for property in data['objects']:
            # Verificar si la propiedad está activa y no eliminada
            if property.get('deleted_at') is not None or property.get('status') != 2:
                continue

            # Verificar operaciones
            operations = property.get('operations', [])
            valid_operation = False
            operation_price = None
            operation_type = None

            for operation in operations:
                if filters.get('operation_types'):
                    if operation['operation_id'] in filters['operation_types']:
                        valid_operation = True
                        operation_type = operation['operation_type']
                        prices = operation.get('prices', [])
                        if prices:
                            operation_price = prices[0]
                        break
                else:
                    valid_operation = True
                    operation_type = operation['operation_type']
                    prices = operation.get('prices', [])
                    if prices:
                        operation_price = prices[0]
                    break

            if not valid_operation:
                continue

            # Formatear el precio
            price_str = "Precio no especificado"
            if operation_price:
                currency = operation_price.get('currency', '')
                price = operation_price.get('price', 0)
                price_str = f"{currency} {price:,}"

            # Crear objeto de propiedad
            property_info = {
                'title': property.get('publication_title', 'Sin título'),
                'price': price_str,
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

        print(f"Se encontraron {len(results)} propiedades que coinciden con los criterios")
        return results

    except requests.exceptions.RequestException as e:
        print(f"Error al conectarse a la API de Tokko: {e}")
        return None
    except Exception as e:
        print(f"Error inesperado al procesar la búsqueda: {e}")
        return None