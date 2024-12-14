import requests
import json

def extract_filters(user_message):
    message = user_message.lower()

    filters = {
        "status": 2,  # Solo propiedades activas
        "limit": 20,
        "offset": 0,
        "operation_types": [],
        "property_types": [],
        "location": None,
        "price_range": {
            "min": 0,
            "max": None,
            "currency": "USD"
        }
    }

    # Mapeo de operaciones
    if "alquiler temporal" in message:
        filters["operation_types"] = [3]
    elif "alquiler" in message:
        filters["operation_types"] = [2]
    elif any(word in message for word in ["venta", "comprar", "compra"]):
        filters["operation_types"] = [1]

    # Si no se especifica operación, asumimos alquiler
    if not filters["operation_types"]:
        filters["operation_types"] = [2]

    # Mapeo de tipos de propiedad
    property_types = {
        "departamento": 2,
        "casa": 3,
        "ph": 13,
        "oficina": 5,
        "local": 4
    }

    for prop_type, type_id in property_types.items():
        if prop_type in message:
            filters["property_types"].append(type_id)

    # Detectar ubicación
    location_keywords = {
        "ballester": "Villa Ballester",
        "villa ballester": "Villa Ballester",
        "san martin": "San Martín",
        "villa lynch": "Villa Lynch"
    }

    for keyword, location in location_keywords.items():
        if keyword in message:
            filters["location"] = location
            break

    print(f"Filtros generados: {json.dumps(filters, indent=2)}")
    return filters

def search_properties(filters):
    tokko_url = "https://www.tokkobroker.com/api/v1/property/search?key=34430fc661d5b961de6fd53a9382f7a232de3ef0"

    try:
        print(f"Enviando solicitud a Tokko con filtros: {json.dumps(filters, indent=2)}")
        response = requests.post(tokko_url, json=filters)
        response.raise_for_status()
        data = response.json()

        if 'objects' not in data:
            print("No se encontraron propiedades en la respuesta")
            return []

        results = []
        for property in data['objects']:
            # Verificar si la propiedad está activa y no eliminada
            if property.get('deleted_at') or property.get('status') != 2:
                continue

            # Procesar operaciones
            operation_info = None
            for operation in property.get('operations', []):
                if filters.get('operation_types'):
                    if operation['operation_id'] in filters['operation_types']:
                        operation_info = operation
                        break
                else:
                    operation_info = operation
                    break

            if not operation_info:
                continue

            # Obtener precio
            price_info = None
            if operation_info.get('prices'):
                price_info = operation_info['prices'][0]

            # Crear objeto de propiedad
            property_info = {
                'id': property.get('id'),
                'title': property.get('publication_title', 'Sin título'),
                'price': {
                    'currency': price_info.get('currency') if price_info else 'USD',
                    'amount': price_info.get('price', 0) if price_info else 0,
                    'period': price_info.get('period', 0) if price_info else 0
                },
                'location': {
                    'address': property.get('fake_address') or property.get('address', 'Dirección no disponible'),
                    'area': property.get('location', {}).get('name'),
                    'coordinates': {
                        'lat': property.get('geo_lat'),
                        'lon': property.get('geo_long')
                    }
                },
                'characteristics': {
                    'surface': property.get('total_surface'),
                    'covered_surface': property.get('roofed_surface'),
                    'rooms': property.get('room_amount', 0),
                    'bathrooms': property.get('bathroom_amount', 0),
                    'bedrooms': property.get('suite_amount', 0),
                    'property_type': property.get('type', {}).get('name'),
                    'operation_type': operation_info.get('operation_type')
                },
                'features': {
                    'expenses': property.get('expenses', 0),
                    'disposition': property.get('disposition'),
                    'condition': property.get('property_condition')
                },
                'amenities': [tag.get('name') for tag in property.get('tags', []) if tag.get('name')],
                'images': [photo.get('image') for photo in property.get('photos', [])[:3]],
                'reference_code': property.get('reference_code', '')
            }

            results.append(property_info)

        print(f"Se encontraron {len(results)} propiedades que coinciden con los criterios")
        return results

    except requests.exceptions.RequestException as e:
        print(f"Error en la conexión con Tokko: {str(e)}")
        return None
    except Exception as e:
        print(f"Error procesando datos: {str(e)}")
        return None