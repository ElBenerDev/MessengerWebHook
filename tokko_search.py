import requests
import logging
import sys
import os
from typing import Dict, List, Optional
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

class TokkoManager:
    def __init__(self):
        self.api_key = os.getenv('TOKKO_API_KEY', "34430fc661d5b961de6fd53a9382f7a232de3ef0")
        self.api_url = "https://www.tokkobroker.com/api/v1/property/"

    def search_properties(self, **kwargs) -> Dict:
        """
        Búsqueda de propiedades con filtros precisos
        """
        try:
            # Preparar parámetros para la API
            params = {
                "key": self.api_key,
                "limit": kwargs.get('limit', 10),
                "order_by": kwargs.get('order_by', '-publication_date')
            }

            # Agregar parámetros de búsqueda específicos
            search_params = [
                'operation_type', 
                'property_type', 
                'location', 
                'neighborhood'
            ]

            for param in search_params:
                if param in kwargs:
                    params[param] = kwargs[param]

            # Realizar solicitud a la API
            response = requests.get(self.api_url, params=params)

            if response.status_code != 200:
                return {
                    "error": "No se pudo conectar con el sistema de búsqueda",
                    "status_code": response.status_code
                }

            data = response.json()
            properties = data.get('objects', [])

            # Filtrado adicional de propiedades
            filtered_properties = self._filter_properties(properties, kwargs)

            if not filtered_properties:
                return {
                    "message": "No se encontraron propiedades que coincidan con los criterios",
                    "total": 0,
                    "properties": []
                }

            return {
                "total": len(filtered_properties),
                "properties": filtered_properties
            }

        except Exception as e:
            logging.error(f"Error en búsqueda: {str(e)}")
            return {
                "error": "Ocurrió un error al buscar propiedades",
                "details": str(e)
            }

    def _filter_properties(self, properties: List[Dict], search_criteria: Dict) -> List[Dict]:
        """
        Filtrado avanzado de propiedades
        """
        filtered_props = []

        for prop in properties:
            # Verificaciones de validez
            if not self._is_valid_property(prop):
                continue

            # Verificar criterios de búsqueda específicos
            matches_criteria = True
            for key, value in search_criteria.items():
                if key == 'operation_type':
                    # Verificar tipo de operación en las operaciones de la propiedad
                    if not any(op.get('operation_type') == value for op in prop.get('operations', [])):
                        matches_criteria = False
                        break

                elif key == 'property_type':
                    # Verificar tipo de propiedad
                    if prop.get('type', {}).get('name') != value:
                        matches_criteria = False
                        break

            if matches_criteria:
                filtered_props.append(prop)

        return filtered_props

    def _is_valid_property(self, prop: Dict) -> bool:
        """
        Verificar si la propiedad es válida y está disponible
        """
        checks = [
            # Verificar que tenga URL pública válida
            prop.get('public_url', '').startswith('http'),

            # Verificar que no esté eliminada
            prop.get('deleted_at') is None,

            # Verificar que tenga al menos una operación activa
            any(
                op.get('status', '').lower() in ['disponible', 'active', 'activa'] 
                for op in prop.get('operations', [])
            )
        ]

        return all(checks)

def search_properties(message: str = None, **kwargs) -> Dict:
    """
    Función para buscar propiedades con extracción inteligente de parámetros
    """
    tokko_manager = TokkoManager()

    # Mapeo de palabras clave a parámetros de API
    keyword_mappings = {
        'operation_type': {
            'alquiler': 'Rent',
            'renta': 'Rent',
            'venta': 'Sale',
            'compra': 'Sale'
        },
        'property_type': {
            'departamento': 'Apartment',
            'depto': 'Apartment',
            'casa': 'House',
            'ph': 'PH',
            'terreno': 'Land',
            'monoambiente': 'Studio'
        },
        'location': {
            'villa ballester': 'Villa Ballester',
            'san martin': 'San Martín',
            'martinez': 'Martinez'
        }
    }

    # Si se proporciona un mensaje, intentar extraer parámetros
    if message:
        # Convertir mensaje a minúsculas
        message_lower = message.lower()

        # Buscar coincidencias de palabras clave
        for param_type, keywords in keyword_mappings.items():
            for keyword, value in keywords.items():
                if keyword in message_lower:
                    kwargs[param_type] = value

    # Realizar búsqueda
    return tokko_manager.search_properties(**kwargs)

if __name__ == "__main__":
    # Ejemplos de uso
    print(search_properties("Busco departamento en alquiler en Villa Ballester"))
    print(search_properties(operation_type="Rent", property_type="Apartment"))