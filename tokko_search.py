from typing import Dict, List, Optional, Any
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
        self.api_url = "https://www.tokkobroker.com/api/v1/property/"

    def fetch_properties(self, operation_type: str = None) -> List[Dict]:
        """Obtiene propiedades filtradas por tipo de operación"""
        try:
            params = {
                'key': self.api_key,
                'limit': 50,  # Aumentamos el límite para obtener más resultados
                'status': 2,  # Solo propiedades activas
            }

            if operation_type:
                params['operation_type'] = 'rent' if operation_type.lower() == 'alquiler' else 'sale'

            response = requests.get(self.api_url, params=params)
            response.raise_for_status()
            return response.json().get('objects', [])
        except Exception as e:
            logger.error(f"Error fetching properties: {str(e)}")
            return []

    def process_properties(self, operation_type: str = None) -> List[Property]:
        """Procesa y filtra las propiedades"""
        properties = []
        raw_properties = self.fetch_properties(operation_type)

        for prop in raw_properties:
            # Verificar si la propiedad está activa y no eliminada
            if prop.get('status') != 2 or prop.get('deleted_at'):
                continue

            # Obtener operaciones
            operations = prop.get('operations', [])
            if not operations:
                continue

            # Filtrar por tipo de operación
            operation = None
            for op in operations:
                op_type = op.get('operation_type', '').lower()
                if operation_type:
                    if (operation_type.lower() == 'alquiler' and op_type == 'rent') or \
                       (operation_type.lower() == 'venta' and op_type == 'sale'):
                        operation = op
                        break
                else:
                    operation = op
                    break

            if not operation or not operation.get('prices'):
                continue

            # Procesar precio
            price_info = operation['prices'][0]
            price = price_info.get('price', 0)
            currency = price_info.get('currency', '')

            # Crear objeto Property
            property = Property(
                id=str(prop.get('id', '')),
                title=prop.get('publication_title', ''),
                type=prop.get('type', {}).get('name', ''),
                address=prop.get('fake_address', ''),
                location=prop.get('location', {}).get('name', ''),
                price=price,
                currency=currency,
                operation_type='Alquiler' if operation['operation_type'].lower() == 'rent' else 'Venta',
                rooms=prop.get('room_amount', 0),
                bathrooms=prop.get('bathroom_amount', 0),
                surface=float(prop.get('total_surface', 0)),
                expenses=float(prop.get('expenses', 0)),
                photos=[p['image'] for p in prop.get('photos', [])[:3] if p.get('image')],
                url=f"https://ficha.info/p/{prop.get('public_url', '').strip()}",
                description=prop.get('description', '')
            )

            properties.append(property)

        return properties

def format_property_message(properties: List[Property]) -> str:
    """Formatea las propiedades para WhatsApp"""
    if not properties:
        return "No encontré propiedades que coincidan con tu búsqueda."

    message = "Encontré las siguientes propiedades:\n\n"

    for i, prop in enumerate(properties[:5], 1):  # Limitamos a 5 propiedades
        # Formatear precio
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

        # Agregar primera foto si existe
        if prop.photos:
            message += f"{prop.photos[0]}\n\n"

    return message

def search_properties(query: str) -> str:
    """Función principal de búsqueda"""
    manager = PropertyManager()

    # Determinar tipo de operación
    operation_type = None
    if any(word in query.lower() for word in ['alquiler', 'alquilar', 'renta', 'rentar']):
        operation_type = 'Alquiler'
    elif any(word in query.lower() for word in ['venta', 'comprar', 'compra']):
        operation_type = 'Venta'

    # Obtener y filtrar propiedades
    properties = manager.process_properties(operation_type)

    # Filtrar por ubicación si se especifica
    if 'ballester' in query.lower():
        properties = [p for p in properties if 'ballester' in p.location.lower()]

    return format_property_message(properties)