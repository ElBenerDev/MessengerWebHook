import requests
import json
from typing import Dict, List, Optional, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def search_properties(filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    base_url = "https://www.tokkobroker.com/api/v1/property/"
    api_key = "34430fc661d5b961de6fd53a9382f7a232de3ef0"

    # Asegurarnos que solo busque propiedades activas y en alquiler
    base_filters = {
        "status": 2,  # Activa
        "operation_types": [2],  # Solo alquiler
        "limit": 10,
        "order": "-created_at"
    }

    # Combinar los filtros base con los filtros específicos
    filters.update(base_filters)

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

        formatted_results = []
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

                # Solo incluir si tiene precio de alquiler
                if price_info:
                    property_info = {
                        'title': prop.get('publication_title'),
                        'type': prop.get('type', {}).get('name'),
                        'address': prop.get('fake_address'),
                        'price': price_info,
                        'rooms': prop.get('room_amount'),
                        'bathrooms': prop.get('bathroom_amount'),
                        'surface': prop.get('total_surface'),
                        'expenses': prop.get('expenses'),
                        'url': f"https://ficha.info/p/{prop.get('token')}",
                        'condition': prop.get('property_condition'),
                        'photos': [p.get('thumb') for p in prop.get('photos', [])[:1]] if prop.get('photos') else []
                    }
                    formatted_results.append(property_info)

        return formatted_results

    except requests.exceptions.RequestException as e:
        logger.error(f"Error en la búsqueda: {str(e)}")
        return None

def extract_filters(context: Dict) -> Dict[str, Any]:
    filters = {}

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

    # Rango de precios
    if context.get('max_price'):
        filters['max_price'] = context['max_price']
    if context.get('min_price'):
        filters['min_price'] = context['min_price']

    return filters