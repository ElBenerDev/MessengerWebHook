from typing import Dict, List, Optional
import requests
import json
import logging
import pandas as pd
from dataclasses import dataclass
from datetime import datetime
import re

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

    def search_properties(self, operation_type: str = None) -> List[Dict]:
        """
        Búsqueda de propiedades usando el endpoint específico de búsqueda
        """
        operation_type_id = self.get_operation_type_id(operation_type) if operation_type else '2'

        # Estructura modificada según la documentación de Tokko
        search_data = {
            "current_localization_id": "25034",  # Villa Ballester
            "current_localization_type": "division",
            "operation_types": [operation_type_id],
            "property_types": ["2", "13"],  # Departamentos y PH
            "status": ["2"],  # Activa
            "price_from": None,
            "price_to": None,
            "currency": "ARS",
            "with_prices": True
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

            # Guardar respuesta completa para análisis
            with open('last_api_response.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return data.get('objects', [])

        except Exception as e:
            logger.error(f"Error en búsqueda: {str(e)}")
            return []

    def export_tokko_data_to_csv(self) -> str:
        """Exporta todos los datos de la API de Tokko a un CSV para análisis"""
        try:
            # Obtener datos crudos de la API
            raw_properties = self.search_properties()

            # Lista para almacenar los datos procesados
            properties_data = []

            for prop in raw_properties:
                # Procesar cada operación de la propiedad
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
                            'total_surface': prop.get('total_surface'),
                            'covered_surface': prop.get('covered_surface'),
                            'expenses': prop.get('expenses'),
                            'web_price': prop.get('web_price'),
                            'status': prop.get('status'),
                            'has_parking': prop.get('parking_amount', 0) > 0,
                            'floor': prop.get('floor'),
                            'orientation': prop.get('orientation'),
                            'amenities': ', '.join(prop.get('tags', [])),
                            'url': f"https://ficha.info/p/{prop.get('public_url', '').strip()}"
                        }
                        properties_data.append(property_info)

            # Crear DataFrame
            df = pd.DataFrame(properties_data)

            # Generar nombre de archivo con timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'tokko_properties_{timestamp}.csv'

            # Guardar CSV
            df.to_csv(filename, index=False, encoding='utf-8')

            # Generar resumen estadístico
            summary = {
                'total_properties': len(df),
                'by_operation_type': df['operation_type'].value_counts().to_dict(),
                'average_price_rent': df[df['operation_type'] == 'Rent']['price'].mean(),
                'average_price_sale': df[df['operation_type'] == 'Sale']['price'].mean(),
                'by_property_type': df['type'].value_counts().to_dict(),
                'average_surface': df['total_surface'].mean(),
                'rooms_distribution': df['rooms'].value_counts().to_dict()
            }

            # Guardar resumen en JSON
            summary_filename = f'tokko_summary_{timestamp}.json'
            with open(summary_filename, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)

            return f"""
            Datos exportados exitosamente:
            - CSV: {filename}
            - Resumen: {summary_filename}

            Resumen rápido:
            - Total propiedades: {summary['total_properties']}
            - Alquileres: {summary['by_operation_type'].get('Rent', 0)}
            - Ventas: {summary['by_operation_type'].get('Sale', 0)}
            - Precio promedio alquiler: ${summary['average_price_rent']:,.2f}
            - Precio promedio venta: ${summary['average_price_sale']:,.2f}
            """

        except Exception as e:
            logger.error(f"Error exportando datos: {str(e)}")
            return f"Error al exportar datos: {str(e)}"

    def process_properties(self, raw_properties: List[Dict], operation_type: str) -> List[Property]:
        """Procesa las propiedades raw a objetos Property"""
        processed_properties = []
        operation_display = 'Alquiler' if operation_type.lower() == 'alquiler' else 'Venta'
        target_type = 'Rent' if operation_type.lower() == 'alquiler' else 'Sale'

        for prop in raw_properties:
            # Verificar operaciones
            for operation in prop.get('operations', []):
                if operation.get('operation_type') == target_type and operation.get('prices'):
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
                    break

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

    return message

def search_properties(query: str) -> str:
    """Función principal de búsqueda"""
    # Detectar tipo de operación
    operation_type = None
    if any(word in query.lower() for word in ['alquiler', 'alquilar', 'renta']):
        operation_type = 'alquiler'
    elif any(word in query.lower() for word in ['venta', 'comprar', 'compra']):
        operation_type = 'venta'
    else:
        operation_type = 'alquiler'  # default a alquiler si no se especifica

    manager = PropertyManager()
    raw_properties = manager.search_properties(operation_type)
    properties = manager.process_properties(raw_properties, operation_type)
    return format_property_message(properties)

if __name__ == "__main__":
    # Ejemplo de uso
    manager = PropertyManager()

    # Exportar datos a CSV y obtener resumen
    print("Exportando datos de Tokko...")
    export_result = manager.export_tokko_data_to_csv()
    print(export_result)

    # Ejemplo de búsqueda
    query = "Busco departamento en alquiler de 2 ambientes"
    search_result = search_properties(query)
    print("\nResultado de búsqueda:")
    print(search_result)