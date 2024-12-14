import requests
import json
from typing import Dict, List, Optional, Any
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_filters(user_message: str) -> Dict[str, Any]:
    message = user_message.lower()

    filters = {
        "status": 2,  # Solo propiedades activas
        "limit": 20,
        "offset": 0,
        "operation_types": [2],  # Por defecto alquiler
        "property_types": [],
        "location": None
    }

    # Determinar tipo de operación
    if "temporal" in message:
        filters["operation_types"] = [3]  # Alquiler temporal
    elif "venta" in message or "comprar" in message:
        filters["operation_types"] = [1]  # Venta

    # Tipo de propiedad
    if any(word in message for word in ["departamento", "depto", "dpto"]):
        filters["property_types"].append(2)  # Apartment
    if "casa" in message:
        filters["property_types"].append(3)  # House
    if "ph" in message:
        filters["property_types"].append(13)  # PH/Condo

    # Ubicación
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

    logger.info(f"Filtros generados: {json.dumps(filters, indent=2)}")
    return filters

def search_properties(filters: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    tokko_url = "https://www.tokkobroker.com/api/v1/property/search?key=34430fc661d5b961de6fd53a9382f7a232de3ef0"

    try:
        logger.info(f"Enviando solicitud a Tokko con filtros: {json.dumps(filters, indent=2)}")
        response = requests.post(tokko_url, json=filters)
        response.raise_for_status()
        data = response.json()

        if 'objects' not in data:
            logger.warning("No se encontraron propiedades en la respuesta")
            return []

        results = []
        for property in data['objects']:
            # Verificar si la propiedad está activa y no eliminada
            if property.get('deleted_at') or property.get('status') != 2:
                continue

            # Verificar operaciones
            operation_info = None
            for operation in property.get('operations', []):
                if operation['operation_id'] in filters.get('operation_types', []):
                    operation_info = operation
                    break

            if not operation_info:
                continue

            # Obtener precio
            price_info = None
            if operation_info.get('prices'):
                price_info = operation_info['prices'][0]

            # Formatear el precio
            price_str = "Consultar"
            if price_info:
                amount = price_info.get('price', 0)
                currency = price_info.get('currency', '')
                period = price_info.get('period', 0)

                price_str = f"{currency} {amount:,}"
                if period == 1:  # Mensual
                    price_str += " por mes"

            # Crear objeto de propiedad
            property_info = {
                'title': property.get('publication_title', 'Sin título'),
                'address': property.get('fake_address', property.get('address', 'Dirección no disponible')),
                'condition': property.get('property_condition', 'No especificado'),
                'surface': f"{property.get('total_surface', 0)} m²",
                'price': price_str,
                'rooms': property.get('room_amount', 0),
                'bathrooms': property.get('bathroom_amount', 0),
                'expenses': property.get('expenses', 0),
                'description': property.get('description', ''),
                'tags': property.get('tags', []),
                'reference': property.get('reference_code', ''),
                'public_url': property.get('public_url', ''),
                'images': [photo.get('image') for photo in property.get('photos', [])[:3]]
            }

            results.append(property_info)

        logger.info(f"Se encontraron {len(results)} propiedades que coinciden con los criterios")
        return results

    except Exception as e:
        logger.error(f"Error en la búsqueda: {str(e)}")
        return None

def format_property_response(properties: Optional[List[Dict[str, Any]]]) -> str:
    if not properties:
        return "No se encontraron propiedades que coincidan con los criterios de búsqueda."

    if properties is None:
        return "Hubo un error al realizar la búsqueda. Por favor, intente nuevamente."

    response = "📍 Propiedades encontradas:\n\n"

    for prop in properties:
        # Título y tipo de propiedad
        response += f"🏠 *{prop['title']}*\n"
        response += f"📍 Ubicación: {prop['address']}\n"
        response += f"💰 Precio: {prop['price']}\n"
        response += f"📏 Superficie: {prop['surface']}\n"

        if prop['rooms'] > 0:
            response += f"🛏️ Ambientes: {prop['rooms']}\n"
        if prop['bathrooms'] > 0:
            response += f"🚿 Baños: {prop['bathrooms']}\n"
        if prop['expenses'] > 0:
            response += f"💵 Expensas: ${prop['expenses']:,}\n"

        response += f"✨ Estado: {prop['condition']}\n"

        # Agregar URL como hipervínculo
        if prop['public_url']:
            response += f"🔍 [Ver más detalles]({prop['public_url']})\n"

        response += f"📝 Código de referencia: {prop['reference']}\n"

        response += "\n-------------------\n\n"

    return response