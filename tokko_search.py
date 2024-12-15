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

    def _extract_price_info(self, operations: List[Dict]) -> Optional[Dict]:
        """Extrae información de precio y tipo de operación"""
        if not operations:
            return None

        operation = operations[0]
        prices = operation.get('prices', [])
        if not prices:
            return None

        operation_type = operation.get('operation_type', '')
        # Normalizar el tipo de operación
        if operation_type.lower() == 'rent':
            operation_type = 'Alquiler'
        elif operation_type.lower() == 'sale':
            operation_type = 'Venta'

        return {
            'price': prices[0].get('price', 0),
            'currency': prices[0].get('currency', ''),
            'operation_type': operation_type
        }

    def process_properties(self) -> List[Property]:
        """Procesa las propiedades y las convierte en objetos Property"""
        raw_properties = self.fetch_properties()
        processed_properties = []

        for prop in raw_properties:
            # Solo procesar propiedades activas
            if prop.get('status') != 2 or prop.get('deleted_at'):
                continue

            price_info = self._extract_price_info(prop.get('operations', []))
            if not price_info:
                continue

            # Limpiar y formatear la URL
            url = prop.get('public_url', '').strip()
            if url and not url.startswith('http'):
                url = f"https://ficha.info/p/{url}"

            # Procesar fotos (asegurarse de que sean URLs completas)
            photos = []
            for photo in prop.get('photos', [])[:3]:  # Limitamos a 3 fotos
                photo_url = photo.get('image', '')
                if photo_url and not photo_url.startswith('http'):
                    photo_url = f"https:{photo_url}"
                if photo_url:
                    photos.append(photo_url)

            processed_properties.append(Property(
                id=str(prop.get('id', '')),
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
                photos=photos,
                url=url,
                description=prop.get('description', ''),
                status=prop.get('status', 0)
            ))

        self.properties = processed_properties
        return processed_properties

    def search_properties(self, filters: Dict = None) -> List[Property]:
        """Busca propiedades según los filtros especificados"""
        if not self.properties:
            self.process_properties()

        filtered_props = self.properties

        if filters:
            # Filtrar por tipo de operación (prioridad alta)
            if 'operation_type' in filters:
                operation_type = filters['operation_type'].lower()
                filtered_props = [p for p in filtered_props 
                                if p.operation_type.lower() == operation_type]

            # Filtrar por ubicación
            if 'location' in filters:
                location = filters['location'].lower()
                filtered_props = [p for p in filtered_props 
                                if location in p.location.lower()]

            # Filtrar por precio
            if 'min_price' in filters:
                filtered_props = [p for p in filtered_props 
                                if p.price >= filters['min_price']]
            if 'max_price' in filters:
                filtered_props = [p for p in filtered_props 
                                if p.price <= filters['max_price']]

            # Filtrar por habitaciones
            if 'rooms' in filters:
                filtered_props = [p for p in filtered_props 
                                if p.rooms >= filters['rooms']]

        return filtered_props

def format_property_message(properties: List[Property]) -> str:
    """Formatea las propiedades para el mensaje de WhatsApp"""
    if not properties:
        return "No encontré propiedades que coincidan con tu búsqueda."

    message = "Encontré las siguientes propiedades:\n\n"

    for i, prop in enumerate(properties, 1):
        # Formatear precio
        price_str = f"{prop.currency} {prop.price:,.0f}" if prop.price > 0 else "Consultar precio"

        message += f"*{i}. {prop.title}*\n"
        message += f"📍 {prop.address}, {prop.location}\n"
        message += f"💰 {prop.operation_type}: {price_str}\n"

        # Agregar detalles relevantes
        details = []
        if prop.rooms > 0:
            details.append(f"{prop.rooms} amb.")
        if prop.bathrooms > 0:
            details.append(f"{prop.bathrooms} baños")
        if prop.surface > 0:
            details.append(f"{prop.surface:.0f}m²")
        if details:
            message += f"✨ {' | '.join(details)}\n"

        # Agregar expensas si existen
        if prop.expenses > 0:
            message += f"💵 Expensas: ${prop.expenses:,.0f}\n"

        # Agregar link
        message += f"🔍 Ver más: {prop.url}\n\n"

    return message

def search_properties(query: str) -> str:
    """Función principal para buscar propiedades"""
    manager = PropertyManager()

    # Extraer filtros del query
    filters = {}
    query_lower = query.lower()

    # Determinar tipo de operación
    if any(word in query_lower for word in ['alquiler', 'alquilar', 'renta', 'rentar']):
        filters['operation_type'] = 'Alquiler'
    elif any(word in query_lower for word in ['venta', 'comprar', 'compra']):
        filters['operation_type'] = 'Venta'

    # Extraer ubicación
    if 'ballester' in query_lower:
        filters['location'] = 'Ballester'

    # Buscar propiedades
    properties = manager.search_properties(filters)

    # Formatear respuesta
    return format_property_message(properties)