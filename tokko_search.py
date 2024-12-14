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
    base_url = "https://www.tokkobroker.com/api/v1/property/search"
    api_key = "34430fc661d5b961de6fd53a9382f7a232de3ef0"

    # Construir el payload de búsqueda base
    search_data = {
        "current_localization_type": "division",
        "current_localization_id": [25034],  # Villa Ballester
        "operation_types": [2],  # Solo alquiler
        "property_types": filters.get('property_types', [2, 3, 13]),  # Por defecto: Departamentos, casas y PH
        "currency": "ARS",
        "price_from": filters.get('min_price', 0),
        "price_to": filters.get('max_price', 1000000),
        "filters": [
            ["status", "=", 2],  # Propiedades activas
            ["deleted_at", "=", None]  # No eliminadas
        ],
        "limit": 10,
        "offset": 0,
        "order": "DESC",
        "order_by": "created_at"
    }

    # Agregar filtros específicos
    if filters.get('room_amount'):
        search_data['filters'].append(["room_amount", "=", filters['room_amount']])
    if filters.get('bathroom_amount'):
        search_data['filters'].append(["bathroom_amount", "=", filters['bathroom_amount']])

    try:
        logger.info(f"Realizando búsqueda con filtros: {json.dumps(search_data, indent=2)}")

        response = requests.post(
            base_url,
            params={'key': api_key},
            json=search_data,
            headers={'Accept': 'application/json'}
        )

        response.raise_for_status()
        data = response.json()

        logger.info(f"Resultados encontrados: {len(data.get('objects', []))}")

        # Formatear los resultados
        formatted_results = []
        for prop in data.get('objects', []):
            # Obtener el precio de alquiler
            price_info = None
            for op in prop.get('operations', []):
                if op.get('operation_type') == 'Rent':
                    prices = op.get('prices', [])
                    if prices:
                        price = prices[0]
                        if price.get('price'):
                            price_info = f"ARS {price['price']:,}"
                            break

            if price_info:
                # Obtener fotos con URLs limpias
                photos = []
                for photo in prop.get('photos', [])[:3]:  # Limitamos a 3 fotos
                    photo_url = photo.get('image', '').split('?')[0]  # Eliminar parámetros de URL
                    if photo_url:
                        photos.append(photo_url)

                # Formatear detalles adicionales
                details = []
                if prop.get('room_amount'):
                    details.append(f"{prop['room_amount']} ambientes")
                if prop.get('bathroom_amount'):
                    details.append(f"{prop['bathroom_amount']} baños")
                if prop.get('total_surface'):
                    details.append(f"{prop['total_surface']} m²")
                if prop.get('expenses'):
                    details.append(f"Expensas: ARS {prop['expenses']:,}")

                property_info = {
                    'title': prop.get('publication_title', '').strip(),
                    'type': prop.get('type', {}).get('name', ''),
                    'address': prop.get('fake_address', '').strip(),
                    'price': price_info,
                    'details': ' | '.join(details),
                    'description': prop.get('description', '').strip(),
                    'url': f"https://ficha.info/p/{prop.get('token')}",
                    'photos': photos
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
    filters = {}

    # Mapeo de tipos de propiedad
    property_types_map = {
        'departamento': [2],
        'casa': [3],
        'ph': [13],
        'local': [7]
    }

    if context.get('property_type') in property_types_map:
        filters['property_types'] = property_types_map[context['property_type']]

    # Cantidad de ambientes
    if context.get('rooms'):
        filters['room_amount'] = context['rooms']

    # Cantidad de baños
    if context.get('bathrooms'):
        filters['bathroom_amount'] = context['bathrooms']

    # Rango de precios
    if context.get('max_price'):
        filters['max_price'] = context['max_price']
    if context.get('min_price'):
        filters['min_price'] = context['min_price']

    return filters