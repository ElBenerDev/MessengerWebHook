import requests
import logging
import os

logging.basicConfig(level=logging.INFO)

class TokkoManager:
    def __init__(self):
        self.api_key = os.getenv('TOKKO_API_KEY', "34430fc661d5b961de6fd53a9382f7a232de3ef0")
        self.api_url = "https://www.tokkobroker.com/api/v1/property/search"

    def search_properties(self, **kwargs):
        try:
            params = {
                "key": self.api_key,
                "limit": kwargs.get('limit', 10),
                "order_by": kwargs.get('order_by', 'price'),
                "format": "json"
            }

            search_data = {
                "operation_types": kwargs.get('operation_types'),
                "property_types": kwargs.get('property_types'),
                "current_localization_id": kwargs.get('current_localization_id'),
                "price_from": kwargs.get('price_from'),
                "price_to": kwargs.get('price_to'),
                "currency": kwargs.get('currency', 'USD')
            }

            response = requests.post(self.api_url, params=params, json=search_data)
            if response.status_code != 200:
                return {"error": "Error al conectar con la API de Tokko"}

            return response.json()
        except Exception as e:
            logging.error(f"Error en búsqueda: {str(e)}")
            return {"error": str(e)}

def search_properties(message: str):
    manager = TokkoManager()
    return manager.search_properties(operation_types=[1], property_types=[2])