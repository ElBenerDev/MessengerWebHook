import requests
import logging
import sys

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

    def search_properties(self, query: str) -> str:
        try:
            operation_data = self.detect_operation_type(query)

            params = {
                "limit": 10,  # Aumentamos el límite para tener más opciones después de filtrar
                "key": self.api_key,
                "operation_type": operation_data['api_value'],
                "location": "Villa Ballester",
                "property_type": "Apartment",
                "min_rooms": 2,
                "order_by": "-publication_date"
            }

            response = requests.get(self.api_url, params=params)

            if response.status_code != 200:
                return "Lo siento, no pude conectar con el sistema de búsqueda en este momento."

            data = response.json()

            # Filtrar propiedades según criterios específicos
            properties = [p for p in data.get('objects', []) 
                        if p.get('type', {}).get('name') == "Apartment" 
                        and "Villa Ballester" in p.get('location', {}).get('full_location', '')
                        and p.get('status') == 2  # Activo
                        and p.get('room_amount', 0) >= 2]  # Al menos 2 ambientes

            if not properties:
                return f"No encontré departamentos en {operation_data['display_name'].lower()} en Villa Ballester que cumplan con los requisitos."

            result = f"*🏢 Departamentos en {operation_data['display_name']} en Villa Ballester:*\n\n"

            for i, prop in enumerate(properties[:5], 1):  # Limitamos a mostrar solo 5 resultados
                # Obtener precio
                operation = next((op for op in prop.get('operations', []) 
                                if op.get('operation_type') == operation_data['api_value']), None)
                price = "Consultar precio"
                if operation and operation.get('prices'):
                    currency = operation['prices'][0].get('currency', '')
                    amount = operation['prices'][0].get('price', 0)
                    if operation_data['api_value'] == 'Rent':
                        price = f"ARS {amount:,.0f} por mes" if currency == 'ARS' else f"USD {amount:,.0f} por mes"
                    else:
                        price = f"USD {amount:,.0f}"

                # Formatear propiedad
                result += (
                    f"*{i}. {prop.get('publication_title', 'Departamento disponible')}*\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📍 {prop.get('address', 'Consultar dirección')}\n"
                    f"💰 {price}\n"
                    f"📐 {prop.get('total_surface', '0')}m² totales\n"
                )

                # Agregar detalles si existen
                if prop.get('room_amount'):
                    result += f"🛏 {prop.get('room_amount')} ambientes\n"
                if prop.get('bedroom_amount'):
                    result += f"🛋 {prop.get('bedroom_amount')} dormitorios\n"
                if prop.get('bathroom_amount'):
                    result += f"🚿 {prop.get('bathroom_amount')} baños\n"
                if prop.get('expenses'):
                    result += f"💵 Expensas: ARS {prop.get('expenses'):,.0f}\n"
                if prop.get('parking_amount'):
                    result += f"🚗 {prop.get('parking_amount')} cocheras\n"

                # Agregar características adicionales
                features = prop.get('features', [])
                if features:
                    result += "\n📋 Características:\n"
                    for feature in features[:3]:  # Limitamos a 3 características
                        result += f"✓ {feature.get('name', '')}\n"

                # Agregar enlace
                if prop.get('public_url'):
                    result += f"\n🔍 Ver más detalles: {prop.get('public_url')}\n"

                # Agregar primera foto
                main_photo = next((photo['image'] for photo in prop.get('photos', []) 
                                 if photo.get('is_front_cover')), None)
                if main_photo:
                    result += f"\n{main_photo}\n"

                result += "\n"

            return result

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