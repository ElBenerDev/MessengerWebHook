import requests
import json
from typing import Dict, List, Optional, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def search_properties(filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Realiza la búsqueda de propiedades usando la API de Tokko
    """
    base_url = "https://www.tokkobroker.com/api/v1/property/"
    api_key = "34430fc661d5b961de6fd53a9382f7a232de3ef0"

    try:
        response = requests.get(
            base_url,
            params={
                'key': api_key,
                **filters
            },
            headers={'Accept': 'application/json'}
        )

        response.raise_for_status()
        data = response.json()

        # Formatear los resultados para incluir solo la información relevante
        formatted_results = []
        for prop in data:
            if prop.get('status') == 2 and not prop.get('deleted_at'):  # Solo propiedades activas
                # Obtener el precio
                price_info = ""
                if prop.get('operations'):
                    for op in prop['operations']:
                        if op.get('prices'):
                            price = op['prices'][0]
                            price_info = f"{price.get('currency', '')} {price.get('price', '')}"
                            break

                # Obtener la primera foto si existe
                photo_url = ""
                if prop.get('photos') and len(prop.get('photos')) > 0:
                    photo_url = prop['photos'][0].get('thumb', '')

                property_info = {
                    'title': prop.get('publication_title'),
                    'address': prop.get('fake_address'),
                    'price': price_info,
                    'details': prop.get('description_only', ''),
                    'url': f"https://ficha.info/p/{prop.get('token')}",
                    'photo': photo_url,
                    'rooms': prop.get('room_amount'),
                    'bathrooms': prop.get('bathroom_amount'),
                    'surface': prop.get('total_surface'),
                    'condition': prop.get('property_condition'),
                    'expenses': prop.get('expenses')
                }
                formatted_results.append(property_info)

        return formatted_results

    except requests.exceptions.RequestException as e:
        logger.error(f"Error en la búsqueda: {str(e)}")
        return None

def extract_filters(context: Dict) -> Dict[str, Any]:
    """
    Extrae los filtros de búsqueda del contexto
    """
    filters = {
        "status": 2,
        "limit": 20,
        "offset": 0,
        "order": "-created_at"
    }

    # Mapeo de tipos de operación
    operation_types = {
        'alquiler': [2],
        'venta': [1]
    }
    if context.get('operation_type') in operation_types:
        filters['operation_types'] = operation_types[context['operation_type']]

    # Mapeo de tipos de propiedad
    property_types = {
        'departamento': [2],
        'casa': [3],
        'ph': [13],
        'local': [7]
    }
    if context.get('property_type') in property_types:
        filters['property_types'] = property_types[context['property_type']]

    # Ubicación
    if context.get('location'):
        filters['location'] = context['location']

    # Cantidad de ambientes
    if context.get('rooms'):
        filters['room_amount'] = context['rooms']

    return filters