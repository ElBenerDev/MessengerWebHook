# tokko_search.py
from typing import Dict, List, Optional
import requests
import json
import logging
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Property:
    id: str
    title: str
    type: str
    address: str
    location: str
    price: float
    currency: str
    operation_type: str
    rooms: int
    bathrooms: int
    surface: float
    expenses: float
    photos: List[str]
    url: str
    description: str

class PropertyManager:
    def __init__(self):
        self.api_key = "34430fc661d5b961de6fd53a9382f7a232de3ef0"
        self.api_url = "https://www.tokkobroker.com/api/v1/property/search"

    def search_properties(self, operation_type: str = None) -> List[Dict]:
        """
        Búsqueda de propiedades usando el endpoint específico de búsqueda
        """
        # Construir el payload según la estructura correcta de la API
        search_data = {
            "data": {
                "current_localization_id": "25034",  # Villa Ballester
                "current_localization_type": "division",
                "operation_types": ["2"] if operation_type.lower() == "alquiler" else ["1"],
                "property_types": ["2", "13"],  # Departamentos y PH
                "status": ["ACTIVE"],
                "currency": "ARS" if operation_type.lower() == "alquiler" else "USD",
                "order_by": "price",
                "order": "ASC"
            }
        }

        params = {
            "key": self.api_key
        }

        headers = {
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                self.api_url,
                params=params,
                json=search_data,
                headers=headers
            )

            logger.info(f"URL: {response.url}")
            logger.info(f"Request Body: {json.dumps(search_data, indent=2)}")
            logger.info(f"Response Status: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"Error Response: {response.text}")
                return []

            data = response.json()
            return data.get('objects', [])

        except Exception as e:
            logger.error(f"Error en búsqueda: {str(e)}")
            return []

    def process_properties(self, raw_properties: List[Dict], operation_type: str) -> List[Property]:
        processed_properties = []

        for prop in raw_properties:
            # Verificar operaciones
            operations = prop.get('operations', [])
            if not operations:
                continue

            # Encontrar la operación correcta
            operation = None
            for op in operations:
                op_type = op.get('operation_type', '').lower()
                if operation_type.lower() == 'alquiler' and op_type == 'rent':
                    operation = op
                    break
                elif operation_type.lower() == 'venta' and op_type == 'sale':
                    operation = op
                    break

            if not operation or not operation.get('prices'):
                continue

            price_info = operation['prices'][0]

            processed_properties.append(Property(
                id=str(prop.get('id', '')),
                title=prop.get('publication_title', ''),
                type=prop.get('type', {}).get('name', ''),
                address=prop.get('fake_address', ''),
                location=prop.get('location', {}).get('name', ''),
                price=price_info.get('price', 0),
                currency=price_info.get('currency', ''),
                operation_type=operation_type,
                rooms=prop.get('room_amount', 0),
                bathrooms=prop.get('bathroom_amount', 0),
                surface=float(prop.get('total_surface', 0)),
                expenses=float(prop.get('expenses', 0)),
                photos=[p['image'] for p in prop.get('photos', [])[:3] if p.get('image')],
                url=f"https://ficha.info/p/{prop.get('public_url', '').strip()}",
                description=prop.get('description', '')
            ))

        return processed_properties

def format_property_message(properties: List[Property]) -> str:
    if not properties:
        return "No encontré propiedades que coincidan con tu búsqueda."

    message = "Encontré las siguientes propiedades:\n\n"

    for i, prop in enumerate(properties[:5], 1):
        price_str = f"{prop.currency} {prop.price:,.0f}" if prop.price > 0 else "Consultar precio"

        message += f"*{i}. {prop.title}*\n"
        message += f"📍 {prop.address}\n"
        message += f"💰 {prop.operation_type}: {price_str}\n"

        if prop.expenses > 0:
            message += f"💵 Expensas: ${prop.expenses:,.0f}\n"

        if prop.rooms > 0:
            message += f"🏠 {prop.rooms} ambientes\n"

        if prop.surface > 0:
            message += f"📐 {prop.surface:.0f}m²\n"

        message += f"🔍 Ver más detalles: {prop.url}\n\n"

        if prop.photos:
            message += f"{prop.photos[0]}\n\n"

    return message

def search_properties(query: str) -> str:
    manager = PropertyManager()

    operation_type = 'Alquiler' if any(word in query.lower() for word in ['alquiler', 'alquilar', 'renta', 'rentar']) else 'Venta'

    raw_properties = manager.search_properties(operation_type)
    properties = manager.process_properties(raw_properties, operation_type)

    return format_property_message(properties)