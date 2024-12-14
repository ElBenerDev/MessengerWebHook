import requests
import logging
from typing import Dict, Any, Optional, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_property_types():
    """Obtiene los tipos de propiedades disponibles"""
    api_key = "34430fc661d5b961de6fd53a9382f7a232de3ef0"
    response = requests.get(
        "https://www.tokkobroker.com/api/v1/property_type/",
        params={'key': api_key}
    )
    return response.json() if response.status_code == 200 else None

def search_properties(filters: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """
    Realiza una búsqueda de propiedades usando la API de Tokko
    """
    api_key = "34430fc661d5b961de6fd53a9382f7a232de3ef0"
    base_url = "https://www.tokkobroker.com/api/v1/property/"

    # Parámetros base para la búsqueda
    params = {
        'key': api_key,
        'limit': 10,
        'offset': 0,
        'order': '-created_at'  # Ordenar por más recientes primero
    }

    # Añadir filtros específicos
    if filters:
        params.update(filters)

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()

        # Procesar y formatear los resultados
        formatted_properties = []
        for prop in data:
            # Verificar que la propiedad está activa y en alquiler
            if (prop.get('status') == 2 and 
                not prop.get('deleted_at') and 
                any(op.get('operation_type') == 'Rent' for op in prop.get('operations', []))):

                # Obtener el precio de alquiler
                price_info = None
                for op in prop.get('operations', []):
                    if op.get('operation_type') == 'Rent':
                        for price in op.get('prices', []):
                            if price.get('currency') and price.get('price'):
                                price_info = f"{price['currency']} {price['price']:,}"
                                break

                if price_info:
                    # Obtener características principales
                    features = []
                    for tag in prop.get('tags', []):
                        if tag.get('name'):
                            features.append(tag['name'])

                    # Formatear la información de la propiedad
                    property_info = {
                        'id': prop.get('id'),
                        'title': prop.get('publication_title', '').strip(),
                        'type': prop.get('type', {}).get('name', ''),
                        'address': prop.get('fake_address', '').strip(),
                        'price': price_info,
                        'expenses': f"ARS {prop.get('expenses'):,}" if prop.get('expenses') else "Sin expensas",
                        'details': {
                            'rooms': prop.get('room_amount'),
                            'bathrooms': prop.get('bathroom_amount'),
                            'surface': f"{prop.get('total_surface')} m²",
                            'condition': prop.get('property_condition')
                        },
                        'features': features,
                        'url': f"https://ficha.info/p/{prop.get('token')}",
                        'photos': [
                            photo.get('image').split('?')[0]
                            for photo in prop.get('photos', [])[:3]
                            if photo.get('image')
                        ]
                    }
                    formatted_properties.append(property_info)

        return formatted_properties

    except requests.exceptions.RequestException as e:
        logger.error(f"Error en la búsqueda: {str(e)}")
        return None

def extract_filters(context: Dict) -> Dict[str, Any]:
    """
    Extrae y formatea los filtros de búsqueda basados en el contexto
    """
    filters = {
        'status': 2,  # Solo propiedades activas
        'operation_types': [2]  # Solo alquiler
    }

    # Mapeo de tipos de propiedad
    property_types_map = {
        'departamento': [2],
        'casa': [3],
        'ph': [13],
        'local': [7]
    }

    if context.get('property_type') in property_types_map:
        filters['property_types'] = property_types_map[context['property_type']]

    # Ubicación (Villa Ballester por defecto)
    filters['location'] = context.get('location', 25034)  # ID de Villa Ballester

    # Cantidad de ambientes
    if context.get('rooms'):
        filters['room_amount'] = context['rooms']

    # Rango de precios
    if context.get('max_price'):
        filters['max_price'] = context['max_price']
    if context.get('min_price'):
        filters['min_price'] = context['min_price']

    return filters