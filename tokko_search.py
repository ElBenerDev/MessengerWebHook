import requests
import json
from typing import Dict, List, Optional, Any
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_filters(context: Dict) -> Dict[str, Any]:
    """
    Extrae los filtros de búsqueda del contexto de la conversación
    """
    filters = {
        "key": "34430fc661d5b961de6fd53a9382f7a232de3ef0",
        "status": 2,  # Solo propiedades activas
        "limit": 20,
        "offset": 0,
        "order": "-created_at"  # Ordenar por más recientes primero
    }

    # Tipo de operación
    if context.get('operation_type') == 'alquiler':
        filters['operation_types'] = [2]
    elif context.get('operation_type') == 'venta':
        filters['operation_types'] = [1]

    # Tipo de propiedad
    property_types = {
        'departamento': 2,
        'casa': 3,
        'ph': 13,
        'local': 7
    }
    if context.get('property_type') in property_types:
        filters['property_types'] = [property_types[context['property_type']]]

    # Ubicación
    if context.get('location'):
        filters['location'] = context['location']

    # Cantidad de ambientes
    if context.get('rooms'):
        filters['room_amount'] = context['rooms']

    return filters

def search_properties(filters: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """
    Realiza la búsqueda de propiedades usando la API de Tokko
    """
    base_url = "https://www.tokkobroker.com/api/v1/property/"

    try:
        # Realizar la solicitud GET
        logger.info(f"Enviando solicitud a Tokko con filtros: {json.dumps(filters, indent=2)}")
        response = requests.get(
            base_url,
            params=filters,
            headers={'Accept': 'application/json'}
        )

        # Verificar si la respuesta es exitosa
        response.raise_for_status()

        # Procesar la respuesta
        data = response.json()
        if not data:
            logger.warning("No se encontraron propiedades en la respuesta")
            return []

        results = []
        for property in data:
            # Verificar si la propiedad está activa
            if property.get('status') != 2 or property.get('deleted_at'):
                continue

            # Extraer información de la operación
            operation_info = None
            for operation in property.get('operations', []):
                if operation['operation_id'] in filters.get('operation_types', []):
                    operation_info = operation
                    break

            if not operation_info:
                continue

            # Formatear el precio
            price_str = "Consultar"
            if operation_info.get('prices'):
                price_info = operation_info['prices'][0]
                amount = price_info.get('price', 0)
                currency = price_info.get('currency', '')
                period = price_info.get('period', 0)
                price_str = f"{currency} {amount:,}"
                if period == 1:
                    price_str += " por mes"

            # Crear objeto de propiedad formateado
            property_info = {
                'title': property.get('publication_title', 'Sin título'),
                'address': property.get('fake_address', property.get('address', 'Dirección no disponible')),
                'condition': property.get('property_condition', 'No especificado'),
                'surface': f"{property.get('total_surface', 0)} m²",
                'price': price_str,
                'rooms': property.get('room_amount', 0),
                'bathrooms': property.get('bathroom_amount', 0),
                'expenses': property.get('expenses', 0),
                'operation_type': operation_info['operation_type'],
                'url': property.get('public_url', ''),
                'reference': property.get('reference_code', ''),
                'description': property.get('description', ''),
                'location': property.get('location', {}).get('name', 'Ubicación no especificada'),
                'images': [photo.get('image') for photo in property.get('photos', [])[:3] if photo.get('image')]
            }

            results.append(property_info)

        logger.info(f"Se encontraron {len(results)} propiedades que coinciden con los criterios")
        return results

    except requests.exceptions.RequestException as e:
        logger.error(f"Error en la búsqueda: {str(e)}")
        return None

def format_property_response(properties: Optional[List[Dict[str, Any]]]) -> str:
    """
    Formatea la respuesta de las propiedades para mostrar
    """
    if not properties:
        return "No se encontraron propiedades que coincidan con los criterios de búsqueda."

    if properties is None:
        return "Hubo un error al realizar la búsqueda. Por favor, intente nuevamente."

    response = "📍 Encontré estas propiedades que podrían interesarte:\n\n"

    for prop in properties:
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
        if prop['url']:
            response += f"🔍 Más información: {prop['url']}\n"

        response += "\n-------------------\n\n"

    return response