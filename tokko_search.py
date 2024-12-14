from typing import Dict, List, Optional, Any, Union
import sqlite3
import requests
import json
from datetime import datetime
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PropertyDatabase:
    def __init__(self, db_path="properties_cache.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS properties (
                    id INTEGER PRIMARY KEY,
                    data JSON,
                    last_updated TIMESTAMP
                )
            """)
            conn.commit()

    def update_properties(self):
        """Actualiza la base de datos con datos de la API"""
        api_key = "34430fc661d5b961de6fd53a9382f7a232de3ef0"
        url = f"https://www.tokkobroker.com/api/v1/property/?key={api_key}"

        try:
            response = requests.get(url)
            response.raise_for_status()
            properties = response.json().get('objects', [])

            with sqlite3.connect(self.db_path) as conn:
                # Limpiar tabla existente
                conn.execute("DELETE FROM properties")

                # Insertar nuevos datos
                for prop in properties:
                    conn.execute(
                        "INSERT INTO properties (id, data, last_updated) VALUES (?, ?, ?)",
                        (prop.get('id'), json.dumps(prop), datetime.now().isoformat())
                    )
                conn.commit()

            logger.info(f"Base de datos actualizada con {len(properties)} propiedades")
            return True
        except Exception as e:
            logger.error(f"Error actualizando propiedades: {str(e)}")
            return False

    def search_properties(self, query: str = "") -> List[Dict]:
        """
        Busca propiedades según el texto de búsqueda
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                properties = []
                for row in conn.execute("SELECT data FROM properties"):
                    prop = json.loads(row[0])

                    # Verificar si la propiedad está activa y en alquiler
                    if prop.get('status') != 2 or prop.get('deleted_at'):
                        continue

                    is_for_rent = False
                    for operation in prop.get('operations', []):
                        if operation.get('operation_type') == 'Rent':
                            is_for_rent = True
                            break

                    if not is_for_rent:
                        continue

                    # Buscar en el texto
                    searchable_text = f"{prop.get('publication_title', '')} {prop.get('description', '')} {prop.get('location', {}).get('name', '')}".lower()

                    if not query or query.lower() in searchable_text:
                        # Formatear la propiedad para la respuesta
                        formatted_prop = {
                            'id': prop.get('id'),
                            'title': prop.get('publication_title'),
                            'type': prop.get('type', {}).get('name'),
                            'address': prop.get('fake_address'),
                            'location': prop.get('location', {}).get('name'),
                            'rooms': prop.get('room_amount'),
                            'bathrooms': prop.get('bathroom_amount'),
                            'surface': prop.get('total_surface'),
                            'expenses': prop.get('expenses'),
                            'description': prop.get('description'),
                            'url': f"https://ficha.info/p/{prop.get('token')}",
                            'photos': [
                                photo.get('image')
                                for photo in prop.get('photos', [])[:3]
                                if photo.get('image')
                            ],
                            'features': [
                                tag.get('name')
                                for tag in prop.get('tags', [])
                                if tag.get('name')
                            ],
                            'operations': []
                        }

                        # Agregar información de precios
                        for operation in prop.get('operations', []):
                            if operation.get('operation_type') == 'Rent':
                                prices = operation.get('prices', [])
                                if prices:
                                    formatted_prop['operations'].append({
                                        'type': 'Alquiler',
                                        'currency': prices[0].get('currency'),
                                        'price': prices[0].get('price')
                                    })

                        properties.append(formatted_prop)

                return properties

        except Exception as e:
            logger.error(f"Error buscando propiedades: {str(e)}")
            return []

def format_property_message(properties: List[Dict]) -> str:
    """Formatea las propiedades para mostrar en el mensaje de WhatsApp"""
    if not properties:
        return "No encontré propiedades que coincidan con tu búsqueda."

    message = "Encontré las siguientes propiedades en alquiler:\n\n"

    for i, prop in enumerate(properties, 1):
        message += f"*{i}. {prop['title']}*\n"
        if prop['location']:
            message += f"📍 *Ubicación*: {prop['location']}\n"
        message += f"🏠 *Dirección*: {prop['address']}\n"

        # Agregar precios
        for operation in prop['operations']:
            message += f"💰 *{operation['type']}*: {operation['currency']} {operation['price']:,}\n"

        if prop['expenses']:
            message += f"📊 *Expensas*: ARS {prop['expenses']:,}\n"

        # Agregar detalles
        details = []
        if prop['rooms']:
            details.append(f"{prop['rooms']} ambientes")
        if prop['bathrooms']:
            details.append(f"{prop['bathrooms']} baños")
        if prop['surface']:
            details.append(f"{prop['surface']} m²")
        if details:
            message += f"ℹ️ *Detalles*: {', '.join(details)}\n"

        # Agregar características
        if prop['features']:
            message += f"✨ *Características*: {', '.join(prop['features'])}\n"

        # Agregar link directo
        message += f"🔍 *Ver ficha completa*: {prop['url']}\n"

        # Indicar que hay fotos disponibles
        if prop['photos']:
            for photo_url in prop['photos']:
                message += f"{photo_url}\n"

        message += "\n-------------------\n\n"

    return message

def search_properties(query: str = "") -> Dict:
    """Función principal para buscar y formatear propiedades"""
    db = PropertyDatabase()

    # Actualizar base de datos
    db.update_properties()

    # Realizar búsqueda
    properties = db.search_properties(query)

    # Formatear resultados
    return format_property_message(properties)