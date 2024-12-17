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
        Búsqueda de propiedades con parámetros flexibles
        """
        try:
            # Preparar parámetros para la API
            params = {
                "key": self.api_key,
                "limit": kwargs.get('limit', 10),
                "order_by": kwargs.get('order_by', '-publication_date')
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

            if not properties:
                return {
                    "message": "No se encontraron propiedades",
                    "total": 0,
                    "properties": []
                }

            # Devolver la respuesta completa de la API
            return {
                "total": len(properties),
                "properties": properties
            }

        except Exception as e:
            logging.error(f"Error en búsqueda: {str(e)}")
            return {
                "error": "Ocurrió un error al buscar propiedades",
                "details": str(e)
            }

def search_properties(message: str = None, **kwargs) -> Dict:
    """
    Función para buscar propiedades
    """
    tokko_manager = TokkoManager()

    # Si se proporciona un mensaje, intentar extraer parámetros
    if message:
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
    print(search_properties("Busco departamento en alquiler"))
    print(search_properties(operation_type="Rent", property_type="Apartment"))