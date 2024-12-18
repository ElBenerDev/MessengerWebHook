import requests
import logging
import sys
import os
from typing import Dict, Optional

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
        Búsqueda de propiedades con filtros adicionales para asegurar disponibilidad
        """
        try:
            # Preparar parámetros para la API
            params = {
                "key": self.api_key,
                "limit": kwargs.get('limit', 10),
                "order_by": kwargs.get('order_by', '-publication_date'),
                # Filtros adicionales para asegurar disponibilidad
                "status": "Disponible",  # Asumiendo que existe este filtro
                "deleted_at__isnull": True  # Propiedades no eliminadas
            }

            # Agregar todos los parámetros proporcionados
            for key, value in kwargs.items():
                if key not in ['limit', 'order_by', 'key']:
                    params[key] = value

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
            available_properties = [
                prop for prop in properties 
                if self._is_property_available(prop)
            ]

            if not available_properties:
                return {
                    "message": "No se encontraron propiedades disponibles",
                    "total": 0,
                    "properties": []
                }

            return {
                "total": len(available_properties),
                "properties": available_properties
            }

        except Exception as e:
            logging.error(f"Error en búsqueda: {str(e)}")
            return {
                "error": "Ocurrió un error al buscar propiedades",
                "details": str(e)
            }

    def _is_property_available(self, prop: Dict) -> bool:
        """
        Verificar si una propiedad está realmente disponible
        """
        # Verificaciones múltiples de disponibilidad
        checks = [
            # Verificar que no esté eliminada
            prop.get('deleted_at') is None,

            # Verificar estado de publicación
            prop.get('status', '').lower() in ['disponible', 'active', 'activa'],

            # Verificar que tenga al menos una operación activa
            any(
                op.get('status', '').lower() in ['disponible', 'active', 'activa'] 
                for op in prop.get('operations', [])
            ),

            # Verificar que tenga URL pública válida
            prop.get('public_url', '').startswith('http')
        ]

        return all(checks)

def search_properties(message: str = None, **kwargs) -> Dict:
    """
    Función para buscar propiedades
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
            'terreno': 'Land'
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