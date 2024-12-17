import requests
import logging
import sys

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def search_properties(query: str) -> str:
    """Función principal que busca propiedades"""
    try:
        tokko = TokkoManager()
        return tokko.search_properties(query)
    except Exception as e:
        logging.error(f"❌ Error en search_properties: {str(e)}")
        return "Lo siento, ocurrió un error al buscar propiedades"

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
            operation = next((op for op in prop.get('operations', []) if op.get('prices')), None)
            price_str = f"{operation['prices'][0].get('currency', '')} {operation['prices'][0].get('price', 0):,.0f}" if operation else "Precio a consultar"
            expenses = f"(Expensas: ${prop.get('expenses'):,.0f})" if prop.get('expenses') else ""
            surface = prop.get('total_surface', prop.get('surface', '0'))

            result = (
                f"🏠 {prop.get('publication_title', 'Sin título')}\n"
                f"💰 {price_str} {expenses}\n"
                f"📍 {prop.get('address', 'Dirección no disponible')}\n"
                f"📏 {surface}m² | "
                f"🛏 {prop.get('room_amount', 0)} amb | "
                f"🚿 {prop.get('bathroom_amount', 0)} baños\n"
                f"📌 {prop.get('location', {}).get('name', 'Ubicación no especificada')}\n"
                f"🔍 Ref: {prop.get('reference_code', '')}\n"
            )

            if prop.get('public_url'):
                result += f"➡️ Más info: {prop.get('public_url')}\n"

            return result
        except Exception as e:
            logging.error(f"Error formateando propiedad: {str(e)}")
            return None

    def search_properties(self, query: str) -> str:
        try:
            logging.info(f"🔍 BÚSQUEDA: {query}")

            operation_data = self.detect_operation_type(query)
            logging.info(f"🏷️ Tipo de operación: {operation_data['display_name']}")

            params = {
                "limit": 5,
                "key": self.api_key,
                "operation_type": operation_data['api_value']
            }

            response = requests.get(self.api_url, params=params)

            if response.status_code != 200:
                logging.error(f"❌ Error en la API: {response.status_code}")
                return "Lo siento, ocurrió un error al consultar la API"

            data = response.json()
            properties = data.get('objects', [])

            if not properties:
                return f"No encontré propiedades en {operation_data['display_name'].lower()}"

            total_count = data.get('meta', {}).get('total_count', len(properties))
            formatted_results = [self.format_property(prop) for prop in properties if self.format_property(prop)]

            summary = (
                f"📊 Resultados para {operation_data['display_name']}:\n"
                f"📍 Encontradas {total_count} propiedades\n"
                f"👀 Mostrando {len(formatted_results)} resultados\n"
                f"{'-'*40}\n\n"
            )

            return summary + "\n\n".join(formatted_results)

        except Exception as e:
            logging.error(f"❌ Error: {str(e)}")
            return "Lo siento, ocurrió un error al buscar propiedades"

if __name__ == "__main__":
    # Ejemplo de uso
    result = search_properties("departamento en alquiler")
    print(result)