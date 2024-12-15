from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import requests
import json
import logging
from datetime import datetime

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
    features: List[str]
    photos: List[str]
    url: str
    description: str
    status: int

class PropertyManager:
    def __init__(self):
        self.api_key = "34430fc661d5b961de6fd53a9382f7a232de3ef0"
        self.api_url = "https://www.tokkobroker.com/api/v1/property/"
        self.properties = []
        self.last_update = None

    def fetch_properties(self) -> List[Dict]:
        """Obtiene todas las propiedades de la API"""
        try:
            params = {
                'limit': 0,
                'key': self.api_key
            }
            response = requests.get(self.api_url, params=params)
            response.raise_for_status()
            return response.json().get('objects', [])
        except Exception as e:
            logger.error(f"Error fetching properties: {str(e)}")
            return []

    def process_properties(self) -> List[Property]:
        """Procesa las propiedades y las convierte en objetos Property"""
        raw_properties = self.fetch_properties()
        processed_properties = []

        for prop in raw_properties:
            # Solo procesar propiedades activas
            if prop.get('status') != 2 or prop.get('deleted_at'):
                continue

            # Extraer información de precio y operación
            price_info = self._extract_price_info(prop.get('operations', []))
            if not price_info:
                continue

            processed_properties.append(Property(
                id=prop.get('id', ''),
                title=prop.get('publication_title', ''),
                type=prop.get('type', {}).get('name', ''),
                address=prop.get('fake_address', ''),
                location=prop.get('location', {}).get('name', ''),
                price=price_info['price'],
                currency=price_info['currency'],
                operation_type=price_info['operation_type'],
                rooms=prop.get('room_amount', 0),
                bathrooms=prop.get('bathroom_amount', 0),
                surface=float(prop.get('total_surface', 0)),
                expenses=float(prop.get('expenses', 0)),
                features=[tag.get('name') for tag in prop.get('tags', []) if tag.get('name')],
                photos=[photo.get('image') for photo in prop.get('photos', [])[:3] if photo.get('image')],
                url=prop.get('public_url', ''),
                description=prop.get('description', ''),
                status=prop.get('status', 0)
            ))

        self.properties = processed_properties
        self.last_update = datetime.now()
        return processed_properties

    def _extract_price_info(self, operations: List[Dict]) -> Optional[Dict]:
        """Extrae información de precio y tipo de operación"""
        if not operations:
            return None

        operation = operations[0]
        prices = operation.get('prices', [])
        if not prices:
            return None

        return {
            'price': prices[0].get('price', 0),
            'currency': prices[0].get('currency', ''),
            'operation_type': 'Alquiler' if operation.get('operation_type') == 'Rent' else 'Venta'
        }

    def search_properties(self, filters: Dict = None) -> List[Property]:
        """Busca propiedades según los filtros especificados"""
        if not self.properties or not self.last_update:
            self.process_properties()

        filtered_props = self.properties

        if filters:
            if 'operation_type' in filters:
                filtered_props = [p for p in filtered_props if p.operation_type.lower() == filters['operation_type'].lower()]

            if 'min_price' in filters:
                filtered_props = [p for p in filtered_props if p.price >= filters['min_price']]

            if 'max_price' in filters:
                filtered_props = [p for p in filtered_props if p.price <= filters['max_price']]

            if 'location' in filters:
                filtered_props = [p for p in filtered_props if filters['location'].lower() in p.location.lower()]

            if 'rooms' in filters:
                filtered_props = [p for p in filtered_props if p.rooms >= filters['rooms']]

        return filtered_props

def format_property_message(properties: List[Property]) -> str:
    """Formatea las propiedades para el mensaje de WhatsApp"""
    if not properties:
        return "No encontré propiedades que coincidan con tu búsqueda."

    message = "Encontré las siguientes propiedades:\n\n"

    for i, prop in enumerate(properties, 1):
        message += f"*{i}. {prop.title}*\n"
        message += f"📍 *Ubicación*: {prop.location}\n"
        message += f"🏠 *Dirección*: {prop.address}\n"
        message += f"💰 *{prop.operation_type}*: {prop.currency} {prop.price:,}\n"

        if prop.expenses > 0:
            message += f"📊 *Expensas*: ARS {prop.expenses:,}\n"

        details = []
        if prop.rooms:
            details.append(f"{prop.rooms} ambientes")
        if prop.bathrooms:
            details.append(f"{prop.bathrooms} baños")
        if prop.surface:
            details.append(f"{prop.surface} m²")

        if details:
            message += f"ℹ️ *Detalles*: {', '.join(details)}\n"

        if prop.features:
            message += f"✨ *Características*: {', '.join(prop.features)}\n"

        message += f"🔍 *Ver más*: {prop.url}\n\n"
        message += "-------------------\n\n"

    return message

def search_properties(query: str) -> str:
    """Función principal para buscar propiedades"""
    manager = PropertyManager()

    # Extraer filtros del query
    filters = {}
    if 'alquiler' in query.lower():
        filters['operation_type'] = 'Alquiler'
    if 'venta' in query.lower():
        filters['operation_type'] = 'Venta'

    # Buscar propiedades
    properties = manager.search_properties(filters)

    # Formatear respuesta
    return format_property_message(properties)