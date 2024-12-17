from typing import Dict, List, Optional
import requests
import json
import logging
import pandas as pd
import re
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

    def get_operation_type_id(self, operation_type: str) -> str:
        """Convierte el tipo de operación en texto al ID correspondiente"""
        operation_types = {
            'alquiler': '2',
            'venta': '1',
            'temporal': '3'
        }
        return operation_types.get(operation_type.lower(), '2')

    def search_properties(self, 
                         operation_type: str = None,
                         rooms: int = None,
                         location_id: str = "25034") -> List[Dict]:
        """
        Búsqueda de propiedades con filtros específicos
        """
        # Determinar tipo de operación
        operation_type_id = self.get_operation_type_id(operation_type) if operation_type else '2'

        search_data = {
            "data": {
                "current_localization_id": location_id,
                "current_localization_type": "division",
                "operation_types": [operation_type_id],
                "property_types": ["2", "13"],  # Departamentos y PH
                "filters": [
                    ["status", "=", "2"],  # Activa
                    ["deleted_at", "=", None],  # No eliminada
                    ["web_price", "=", True]  # Disponible al público
                ],
                "order_by": "price",
                "order": "ASC"
            }
        }

        # Agregar filtro de ambientes si se especifica
        if rooms:
            search_data["data"]["filters"].append(["room_amount", "=", str(rooms)])

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

            # Guardar respuesta completa para análisis
            with open('last_api_response.json', 'w') as f:
                json.dump(data, f, indent=2)

            return self.filter_properties(data.get('objects', []), operation_type)

        except Exception as e:
            logger.error(f"Error en búsqueda: {str(e)}")
            return []

    def filter_properties(self, properties: List[Dict], operation_type: str) -> List[Dict]:
        """Filtra las propiedades según el tipo de operación"""
        operation_type_map = {
            'alquiler': 'Rent',
            'venta': 'Sale',
            'temporal': 'Temporary'
        }

        target_operation = operation_type_map.get(operation_type.lower() if operation_type else 'alquiler')
        filtered_properties = []

        for prop in properties:
            if not prop.get('operations'):
                continue

            for op in prop.get('operations', []):
                if (op.get('operation_type') == target_operation and 
                    op.get('prices') and 
                    op['prices'][0].get('price') > 0):
                    filtered_properties.append(prop)
                    break

        return filtered_properties

    def process_properties(self, raw_properties: List[Dict], operation_type: str) -> List[Property]:
        """Procesa las propiedades raw a objetos Property"""
        processed_properties = []
        operation_display = 'Alquiler' if operation_type.lower() == 'alquiler' else 'Venta'

        for prop in raw_properties:
            # Verificar operaciones
            operations = prop.get('operations', [])
            if not operations:
                continue

            # Encontrar la operación correcta
            operation = None
            target_type = 'Rent' if operation_type.lower() == 'alquiler' else 'Sale'

            for op in operations:
                if op.get('operation_type') == target_type:
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
                operation_type=operation_display,
                rooms=prop.get('room_amount', 0),
                bathrooms=prop.get('bathroom_amount', 0),
                surface=float(prop.get('total_surface', 0) or 0),
                expenses=float(prop.get('expenses', 0) or 0),
                photos=[p['image'] for p in prop.get('photos', [])[:3] if p.get('image')],
                url=f"https://ficha.info/p/{prop.get('public_url', '').strip()}",
                description=prop.get('description', '')
            ))

        return processed_properties

def analyze_api_response(properties: List[Dict]) -> pd.DataFrame:
    """Analiza y guarda la respuesta de la API en un CSV"""
    properties_data = []

    for prop in properties:
        for operation in prop.get('operations', []):
            if operation.get('prices'):
                property_info = {
                    'id': prop.get('id'),
                    'title': prop.get('publication_title'),
                    'type': prop.get('type', {}).get('name'),
                    'address': prop.get('fake_address'),
                    'location': prop.get('location', {}).get('name'),
                    'operation_type': operation.get('operation_type'),
                    'price': operation['prices'][0].get('price'),
                    'currency': operation['prices'][0].get('currency'),
                    'rooms': prop.get('room_amount'),
                    'bathrooms': prop.get('bathroom_amount'),
                    'surface': prop.get('total_surface'),
                    'expenses': prop.get('expenses'),
                }
                properties_data.append(property_info)

    df = pd.DataFrame(properties_data)
    df.to_csv('properties_analysis.csv', index=False)
    return df

def format_property_message(properties: List[Property]) -> str:
    """Formatea las propiedades en un mensaje legible"""
    if not properties:
        return "No encontré propiedades disponibles que coincidan con tu búsqueda en este momento. ¿Te gustaría modificar algunos criterios de búsqueda?"

    message = f"Encontré {len(properties)} propiedades que coinciden con tu búsqueda:\n\n"

    for i, prop in enumerate(properties[:5], 1):
        price_str = f"{prop.currency} {prop.price:,.0f}" if prop.price > 0 else "Consultar precio"

        message += f"*{i}. {prop.title}*\n"
        message += f"📍 {prop.address}\n"
        message += f"💰 {prop.operation_type}: {price_str}\n"

        if prop.expenses > 0:
            message += f"💵 Expensas: ${prop.expenses:,.0f}\n"

        if prop.rooms > 0:
            message += f"🏠 {prop.rooms} ambiente{'s' if prop.rooms > 1 else ''}\n"

        if prop.surface > 0:
            message += f"📐 {prop.surface:.0f}m²\n"

        message += f"🔍 Ver más detalles: {prop.url}\n\n"

        if prop.photos:
            message += f"{prop.photos[0]}\n\n"

    return message

def search_properties(query: str) -> str:
    """Función principal de búsqueda"""
    # Detectar tipo de operación
    operation_type = None
    if any(word in query.lower() for word in ['alquiler', 'alquilar', 'renta']):
        operation_type = 'alquiler'
    elif any(word in query.lower() for word in ['venta', 'comprar', 'compra']):
        operation_type = 'venta'

    # Detectar cantidad de ambientes
    rooms = None
    rooms_match = re.search(r'(\d+)\s*ambientes?', query.lower())
    if rooms_match:
        rooms = int(rooms_match.group(1))

    # Realizar búsqueda
    manager = PropertyManager()
    raw_properties = manager.search_properties(operation_type=operation_type, rooms=rooms)

    # Analizar resultados
    analyze_api_response(raw_properties)

    # Procesar y formatear resultados
    properties = manager.process_properties(raw_properties, operation_type or 'alquiler')
    return format_property_message(properties)

if __name__ == "__main__":
    # Ejemplo de uso
    query = "Busco departamento en alquiler de 2 ambientes"
    result = search_properties(query)
    print(result)