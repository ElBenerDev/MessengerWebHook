import requests
import logging
import sys

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

class TokkoManager:
    def __init__(self):
        self.api_key = "34430fc661d5b961de6fd53a9382f7a232de3ef0"
        self.api_url = "https://www.tokkobroker.com/api/v1/property/"
        self.operation_types = {
            'rent': {
                'keywords': ['alquiler', 'alquilar', 'renta', 'rentar'],
                'api_value': 'Rent',
                'display_name': 'Alquiler'
            },
            'sale': {
                'keywords': ['venta', 'compra', 'comprar', 'vender'],
                'api_value': 'Sale',
                'display_name': 'Venta'
            }
        }

    def detect_operation_type(self, query: str) -> dict:
        query_lower = query.lower()
        for op_type, data in self.operation_types.items():
            if any(keyword in query_lower for keyword in data['keywords']):
                return data
        return self.operation_types['sale']

    def format_property(self, prop):
        try:
            # Obtener el precio
            operation = next((op for op in prop.get('operations', []) if op.get('prices')), None)
            price_str = f"{operation['prices'][0].get('currency', '')} {operation['prices'][0].get('price', 0):,.0f}" if operation else "Precio a consultar"

            # Obtener la primera imagen
            main_photo = next((photo['image'] for photo in prop.get('photos', []) if photo.get('is_front_cover')), "")

            # Formatear el mensaje para WhatsApp
            result = (
                f"🏠 *{prop.get('publication_title', 'Propiedad disponible')}*\n"
                f"💰 {price_str}\n"
                f"📍 {prop.get('address', 'Dirección a consultar')}\n"
                f"📏 {prop.get('total_surface', '0')}m² | "
                f"🛏 {prop.get('room_amount', 0)} amb | "
                f"🚿 {prop.get('bathroom_amount', 0)} baños\n"
                f"🔍 Ref: {prop.get('reference_code', '')}\n"
            )

            # Agregar gastos si existen
            if prop.get('expenses'):
                result += f"💵 Expensas: ${prop.get('expenses'):,.0f}\n"

            # Agregar enlace de la propiedad
            if prop.get('public_url'):
                result += f"➡️ Ver más detalles: {prop.get('public_url')}\n"

            # Agregar imagen si existe
            if main_photo:
                result += f"🖼 {main_photo}\n"

            return result
        except Exception as e:
            logging.error(f"Error formateando propiedad: {str(e)}")
            return None

    def search_properties(self, query: str) -> str:
        try:
            operation_data = self.detect_operation_type(query)

            params = {
                "limit": 5,
                "key": self.api_key,
                "operation_type": operation_data['api_value']
            }

            response = requests.get(self.api_url, params=params)

            if response.status_code != 200:
                return "Lo siento, no pude conectar con el sistema de búsqueda en este momento."

            data = response.json()
            properties = data.get('objects', [])

            if not properties:
                return f"No encontré propiedades en {operation_data['display_name'].lower()} en esta zona."

            formatted_results = [self.format_property(prop) for prop in properties if self.format_property(prop)]

            if not formatted_results:
                return "No pude encontrar propiedades que coincidan con tu búsqueda."

            summary = (
                f"*📊 Encontré {len(formatted_results)} propiedades en {operation_data['display_name'].lower()}:*\n"
                f"{'-'*40}\n\n"
            )

            return summary + "\n\n".join(formatted_results)

        except Exception as e:
            logging.error(f"❌ Error: {str(e)}")
            return "Lo siento, ocurrió un error al buscar propiedades."

def search_properties(query: str) -> str:
    """Función principal que busca propiedades"""
    try:
        tokko = TokkoManager()
        return tokko.search_properties(query)
    except Exception as e:
        logging.error(f"❌ Error en search_properties: {str(e)}")
        return "Lo siento, ocurrió un error al buscar propiedades"

if __name__ == "__main__":
    # Ejemplo de uso
    result = search_properties("departamento en alquiler en Villa Ballester")
    print(result)