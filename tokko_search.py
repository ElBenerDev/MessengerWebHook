import requests
import json
from typing import Dict, List, Optional, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def search_properties(filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Realiza la búsqueda de propiedades usando la API de Tokko y retorna los datos crudos
    """
    base_url = "https://www.tokkobroker.com/api/v1/property/"
    api_key = "34430fc661d5b961de6fd53a9382f7a232de3ef0"

    try:
        # Realizar la solicitud GET
        logger.info(f"Enviando solicitud a Tokko con filtros: {json.dumps(filters, indent=2)}")
        response = requests.get(
            base_url,
            params={
                'key': api_key,
                **filters
            },
            headers={'Accept': 'application/json'}
        )

        # Verificar si la respuesta es exitosa
        response.raise_for_status()

        # Retornar los datos crudos de la respuesta
        data = response.json()
        logger.info(f"Respuesta recibida de Tokko con {len(data) if data else 0} propiedades")
        return data

    except requests.exceptions.RequestException as e:
        logger.error(f"Error en la búsqueda: {str(e)}")
        return None

def extract_filters(context: Dict) -> Dict[str, Any]:
    """
    Extrae los filtros de búsqueda del contexto de la conversación
    """
    filters = {
        "status": 2,  # Solo propiedades activas
        "limit": 20,
        "offset": 0,
        "order": "-created_at"
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

    # Precio máximo
    if context.get('max_price'):
        filters['max_price'] = context['max_price']

    # Precio mínimo
    if context.get('min_price'):
        filters['min_price'] = context['min_price']

    logger.info(f"Filtros generados: {json.dumps(filters, indent=2)}")
    return filters