import requests
import json
from typing import Dict, List, Optional, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_properties() -> Optional[List[Dict[str, Any]]]:
    """
    Obtiene las propiedades directamente desde la API
    """
    api_key = "34430fc661d5b961de6fd53a9382f7a232de3ef0"
    base_url = "https://www.tokkobroker.com/api/v1/property/"

    params = {
        'key': api_key,
        'status': 2,  # Propiedades activas
        'limit': 50,
        'offset': 0
    }

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()

        # Filtrar y formatear propiedades
        properties = []
        for prop in data.get('objects', []):
            # Solo incluir propiedades activas y no eliminadas
            if prop.get('status') == 2 and not prop.get('deleted_at'):
                # Obtener información de operaciones (alquiler/venta)
                operations = []
                for op in prop.get('operations', []):
                    prices = op.get('prices', [])
                    if prices and prices[0].get('price'):
                        operations.append({
                            'type': op.get('operation_type'),
                            'price': prices[0].get('price'),
                            'currency': prices[0].get('currency', 'ARS')
                        })

                # Formatear la información de la propiedad
                property_info = {
                    'id': prop.get('id'),
                    'reference': prop.get('reference_code'),
                    'title': prop.get('publication_title'),
                    'type': prop.get('type', {}).get('name'),
                    'address': prop.get('fake_address'),
                    'location': prop.get('location', {}).get('name'),
                    'rooms': prop.get('room_amount'),
                    'bathrooms': prop.get('bathroom_amount'),
                    'surface': {
                        'total': prop.get('total_surface'),
                        'covered': prop.get('roofed_surface'),
                        'uncovered': prop.get('unroofed_surface')
                    },
                    'expenses': prop.get('expenses'),
                    'features': [
                        tag.get('name') for tag in prop.get('tags', [])
                        if tag.get('name')
                    ],
                    'description': prop.get('description'),
                    'operations': operations,
                    'url': f"https://ficha.info/p/{prop.get('token')}",
                    'photos': [
                        photo.get('image').split('?')[0]
                        for photo in prop.get('photos', [])[:3]
                        if photo.get('image')
                    ]
                }
                properties.append(property_info)

        return properties

    except requests.exceptions.RequestException as e:
        logger.error(f"Error al obtener propiedades: {str(e)}")
        return None

def format_property_message(properties: List[Dict[str, Any]]) -> str:
    """
    Formatea las propiedades para mostrar en el mensaje
    """
    if not properties:
        return "No se encontraron propiedades disponibles."

    message = "Estas son las propiedades disponibles:\n\n"

    for i, prop in enumerate(properties, 1):
        message += f"{i}. **{prop['title']}**\n"
        message += f"   - **Tipo**: {prop['type']}\n"
        message += f"   - **Dirección**: {prop['address']}\n"

        # Agregar precios de operaciones
        for op in prop['operations']:
            message += f"   - **{op['type']}**: {op['currency']} {op['price']:,}\n"

        if prop['expenses']:
            message += f"   - **Expensas**: ARS {prop['expenses']:,}\n"

        # Agregar detalles
        details = []
        if prop['rooms']:
            details.append(f"{prop['rooms']} ambientes")
        if prop['bathrooms']:
            details.append(f"{prop['bathrooms']} baños")
        if prop['surface']['total']:
            details.append(f"{prop['surface']['total']} m² totales")
        if details:
            message += f"   - **Detalles**: {', '.join(details)}\n"

        # Agregar características
        if prop['features']:
            message += f"   - **Características**: {', '.join(prop['features'])}\n"

        message += f"   - **[Ver más información]({prop['url']})**\n"

        # Agregar fotos
        if prop['photos']:
            message += "   - **Fotos**:\n"
            for photo in prop['photos']:
                message += f"     ![Foto]({photo})\n"

        message += "\n"

    return message

def search_properties(filters: Dict[str, Any] = None) -> Optional[str]:
    """
    Función principal para buscar y formatear propiedades
    """
    properties = get_properties()
    if properties is not None:
        # Aplicar filtros si existen
        if filters:
            filtered_properties = []
            for prop in properties:
                matches = True
                for key, value in filters.items():
                    if key in prop and prop[key] != value:
                        matches = False
                        break
                if matches:
                    filtered_properties.append(prop)
            properties = filtered_properties

        return format_property_message(properties)
    return "Lo siento, hubo un error al buscar propiedades."