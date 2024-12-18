import requests
import logging
import os
from typing import Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)

class TokkoManager:
    def __init__(self):
        self.api_key = os.getenv('TOKKO_API_KEY', "34430fc661d5b961de6fd53a9382f7a232de3ef0")
        self.api_url = "https://www.tokkobroker.com/api/v1/property/search"

    def search_properties(self, **kwargs) -> Dict:
        """
        Búsqueda de propiedades con filtros avanzados
        """
        try:
            # Preparar parámetros para la API
            params = {
                "key": self.api_key,
                "limit": kwargs.get('limit', 10),
                "order_by": kwargs.get('order_by', 'price'),
                "order": kwargs.get('order', 'ASC'),
                "format": "json"
            }

            # Construir el cuerpo de la solicitud (JSON)
            search_data = {
                "current_localization_id": kwargs.get('current_localization_id'),
                "current_localization_type": kwargs.get('current_localization_type', 'division'),
                "price_from": kwargs.get('price_from'),
                "price_to": kwargs.get('price_to'),
                "operation_types": kwargs.get('operation_types'),
                "property_types": kwargs.get('property_types'),
                "currency": kwargs.get('currency', 'USD'),
                "filters": kwargs.get('filters', []),
                "with_tags": kwargs.get('with_tags', []),
                "without_tags": kwargs.get('without_tags', [])
            }

            # Realizar solicitud a la API
            response = requests.post(self.api_url, params=params, json=search_data)

            if response.status_code != 200:
                return {
                    "error": "No se pudo conectar con el sistema de búsqueda",
                    "status_code": response.status_code,
                    "details": response.text
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
                if key == 'operation_types':
                    # Verificar tipo de operación en las operaciones de la propiedad
                    if not any(op.get('operation_type') == value for op in prop.get('operations', [])):
                        matches_criteria = False
                        break

                elif key == 'property_types':
                    # Verificar tipo de propiedad
                    if prop.get('type', {}).get('id') not in value:
                        matches_criteria = False
                        break

                elif key == 'current_localization_id':
                    # Verificar ubicación
                    if prop.get('location', {}).get('id') not in value:
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
        'operation_types': {
            'alquiler': [2],  # Rent
            'renta': [2],     # Rent
            'venta': [1],     # Sale
            'compra': [1]     # Sale
        },
        'property_types': {
            'departamento': [2],  # Apartment
            'depto': [2],         # Apartment
            'casa': [3],          # House
            'ph': [4],            # PH
            'terreno': [1],       # Land
            'monoambiente': [2]   # Apartment
        },
        'current_localization_id': {
            'villa ballester': [24728],
            'san martin': [24682],
            'martinez': [24683]
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
    print(search_properties(
        current_localization_id=[24728],
        operation_types=[2],
        property_types=[2],
        price_from=50000,
        price_to=150000
    ))