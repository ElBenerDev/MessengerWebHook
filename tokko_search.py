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

    def search_properties(self, 
                         location_id: str = "25034",
                         operation_type: List[str] = None,
                         property_types: List[str] = None,
                         price_from: Optional[float] = None,
                         price_to: Optional[float] = None,
                         rooms: Optional[int] = None) -> List[Dict]:
        """
        Búsqueda flexible de propiedades
        """
        search_data = {
            "data": {
                "current_localization_id": location_id,
                "current_localization_type": "division",
                "operation_types": operation_type or ["2"],  # 2 = Alquiler por defecto
                "property_types": property_types or ["2", "13"],  # Departamentos y PH por defecto
                "filters": [
                    ["status", "=", "2"],  # Activa
                    ["deleted_at", "=", None],  # No eliminada
                    ["web_price", "=", True],  # Disponible al público
                ],
                "order_by": "price",
                "order": "ASC"
            }
        }

        # Agregar filtros opcionales
        if rooms:
            search_data["data"]["filters"].append(["room_amount", "=", str(rooms)])
        if price_from:
            search_data["data"]["price_from"] = price_from
        if price_to:
            search_data["data"]["price_to"] = price_to

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
            return self.filter_valid_properties(data.get('objects', []))

        except Exception as e:
            logger.error(f"Error en búsqueda: {str(e)}")
            return []

    def filter_valid_properties(self, properties: List[Dict]) -> List[Dict]:
        """Filtra propiedades válidas según sus operaciones"""
        valid_properties = []

        for prop in properties:
            if not prop.get('operations'):
                continue

            # Verificar operaciones válidas
            for op in prop.get('operations', []):
                if (op.get('prices') and 
                    op['prices'][0].get('price') > 0):
                    valid_properties.append(prop)
                    break

        return valid_properties

    def process_properties(self, raw_properties: List[Dict], operation_type: str) -> List[Property]:
        """Procesa las propiedades raw a objetos Property"""
        processed_properties = []

        for prop in raw_properties:
            # Verificar operaciones
            operations = prop.get('operations', [])
            if not operations:
                continue

            # Encontrar la operación correcta
            operation = None
            for op in operations:
                op_type = 'Rent' if operation_type.lower() == 'alquiler' else 'Sale'
                if op.get('operation_type') == op_type:
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

    message += "¿Te gustaría ver más detalles de alguna de estas propiedades?"

    return message

def interpret_user_query(query: str) -> dict:
    """Interpreta la consulta del usuario y extrae parámetros de búsqueda"""
    params = {}

    # Detectar tipo de operación
    if any(word in query.lower() for word in ['alquiler', 'alquilar', 'renta', 'rentar']):
        params['operation_type'] = ["2"]
    elif any(word in query.lower() for word in ['venta', 'comprar', 'compra']):
        params['operation_type'] = ["1"]

    # Detectar tipo de propiedad
    if 'departamento' in query.lower() or 'depto' in query.lower():
        params['property_types'] = ["2"]
    elif 'casa' in query.lower():
        params['property_types'] = ["3"]
    elif 'ph' in query.lower():
        params['property_types'] = ["13"]

    # Detectar cantidad de ambientes
    import re
    ambient_match = re.search(r'(\d+)\s*ambientes?', query.lower())
    if ambient_match:
        params['rooms'] = int(ambient_match.group(1))

    return params

def search_properties(query: str) -> str:
    """Función principal de búsqueda"""
    manager = PropertyManager()
    search_params = interpret_user_query(query)

    # Determinar tipo de operación para el procesamiento
    operation_type = 'Alquiler' if search_params.get('operation_type') == ["2"] else 'Venta'

    raw_properties = manager.search_properties(**search_params)
    properties = manager.process_properties(raw_properties, operation_type)
    return format_property_message(properties)

if __name__ == "__main__":
    # Ejemplo de uso
    query = "Busco departamento en alquiler de 2 ambientes"
    result = search_properties(query)
    print(result)