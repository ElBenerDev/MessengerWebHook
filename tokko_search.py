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
        search_data = {
            "data": {
                "current_localization_id": "25034",  # Villa Ballester
                "current_localization_type": "division",
                "operation_types": ["2"],  # 2 = Alquiler
                "property_types": ["2", "13"],  # Departamentos y PH
                "filters": [
                    ["status", "=", "2"],  # Activa
                    ["deleted_at", "=", None],  # No eliminada
                    ["web_price", "=", True],  # Disponible al público
                ],
                "order_by": "price",
                "order": "ASC"
            }
        }

        try:
            response = requests.post(
                self.api_url,
                params={"key": self.api_key},
                json=search_data,
                headers={"Content-Type": "application/json"}
            )

            logger.info(f"URL: {response.url}")
            logger.info(f"Request Body: {json.dumps(search_data, indent=2)}")
            logger.info(f"Response Status: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"Error Response: {response.text}")
                return []

            data = response.json()
            properties = []

            # Filtrar solo propiedades que realmente están en alquiler
            for prop in data.get('objects', []):
                if not prop.get('operations'):
                    continue

                # Verificar que tenga operación de alquiler activa
                has_active_rent = False
                for op in prop.get('operations', []):
                    if (op.get('operation_type') == 'Rent' and 
                        op.get('prices') and 
                        op['prices'][0].get('price') > 0):
                        has_active_rent = True
                        break

                if has_active_rent:
                    properties.append(prop)

            return properties

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
                if op.get('operation_type') == 'Rent' and operation_type.lower() == 'alquiler':
                    operation = op
                    break

            if not operation or not operation.get('prices'):
                continue

            price_info = operation['prices'][0]

            # Solo procesar si tiene precio y está disponible al público
            if not price_info.get('price') or not prop.get('web_price'):
                continue

            processed_properties.append(Property(
                id=str(prop.get('id', '')),
                title=prop.get('publication_title', ''),
                type=prop.get('type', {}).get('name', ''),
                address=prop.get('fake_address', ''),
                location=prop.get('location', {}).get('name', ''),
                price=price_info.get('price', 0),
                currency=price_info.get('currency', ''),
                operation_type='Alquiler',
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
        return "No encontré propiedades en alquiler disponibles en Villa Ballester en este momento. ¿Te gustaría que busque en otras zonas cercanas?"

    message = "Encontré las siguientes propiedades en alquiler en Villa Ballester:\n\n"

    for i, prop in enumerate(properties[:5], 1):
        price_str = f"{prop.currency} {prop.price:,.0f}" if prop.price > 0 else "Consultar precio"

        message += f"*{i}. {prop.title}*\n"
        message += f"📍 {prop.address}\n"
        message += f"💰 Alquiler: {price_str}\n"

        if prop.expenses > 0:
            message += f"💵 Expensas: ${prop.expenses:,.0f}\n"

        if prop.rooms > 0:
            message += f"🏠 {prop.rooms} ambiente{'s' if prop.rooms > 1 else ''}\n"

        if prop.surface > 0:
            message += f"📐 {prop.surface:.0f}m²\n"

        message += f"🔍 Ver más detalles: {prop.url}\n\n"

        if prop.photos:
            message += f"{prop.photos[0]}\n\n"

    message += "¿Te gustaría ver más detalles de alguna de estas propiedades?"

    return message

def search_properties(query: str) -> str:
    manager = PropertyManager()
    raw_properties = manager.search_properties('Alquiler')
    properties = manager.process_properties(raw_properties, 'Alquiler')
    return format_property_message(properties)