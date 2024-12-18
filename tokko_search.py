import requests
import logging
import os

logging.basicConfig(level=logging.INFO)

class TokkoManager:
    def __init__(self):
        self.api_key = os.getenv("TOKKO_API_KEY", "34430fc661d5b961de6fd53a9382f7a232de3ef0")
        self.api_url = "https://www.tokkobroker.com/api/v1/property/"

    def search_properties(self, **kwargs):
        try:
            params = {
                "key": self.api_key,
                "limit": kwargs.get("limit", 10),
                "operation_types": kwargs.get("operation_types", []),
                "property_types": kwargs.get("property_types", []),
                "price_from": kwargs.get("price_from", 0),
                "price_to": kwargs.get("price_to", 999999999),
                "currency": kwargs.get("currency", "ANY"),
                "location": kwargs.get("location", None)
            }

            params = {k: v for k, v in params.items() if v}

            response = requests.get(self.api_url, params=params)

            if response.status_code != 200:
                return {"error": "Error al conectar con la API de Tokko", "status_code": response.status_code}

            data = response.json()
            properties = data.get("objects", [])

            if not properties:
                return {"message": "No se encontraron propiedades", "total": 0, "properties": []}

            return {"total": len(properties), "properties": properties}

        except Exception as e:
            logging.error(f"Error en búsqueda: {str(e)}")
            return {"error": "Error al buscar propiedades", "details": str(e)}