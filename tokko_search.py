import requests
import json
import pandas as pd
import logging
import sys
from datetime import datetime

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def search_properties(query: str) -> str:
    """Función principal que busca propiedades basada en la consulta del usuario"""
    try:
        tokko = TokkoManager()
        
        # Si no existe la base de datos, la descargamos
        if not os.path.exists(tokko.csv_path):
            tokko.download_all_properties()
            
        # Realizar la búsqueda
        return tokko.search_in_database(query)
        
    except Exception as e:
        logging.error(f"❌ Error en search_properties: {str(e)}")
        return "Lo siento, ocurrió un error al buscar propiedades"

class TokkoManager:
    def __init__(self):
        self.api_key = "34430fc661d5b961de6fd53a9382f7a232de3ef0"
        self.api_url = "https://www.tokkobroker.com/api/v1/property/search"
        self.csv_path = "properties_database.csv"
        
        # Tipos de operación según la API de Tokko
        self.operation_types = {
            "Sale": "Venta",
            "Rent": "Alquiler"
        }

    def download_all_properties(self) -> bool:
        try:
            logging.info("\n" + "="*50)
            logging.info("🔄 INICIANDO DESCARGA DE PROPIEDADES TOKKO API")
            logging.info("="*50)
            
            all_properties = []
            
            for operation_type in self.operation_types.keys():
                logging.info(f"\n📡 Consultando propiedades en {self.operation_types[operation_type]}...")
                
                search_data = {
                    "current_localization_id": "25034",  # Villa Ballester
                    "current_localization_type": "division",
                    "operation_type": operation_type,
                    "with_prices": True
                }

                response = requests.post(
                    self.api_url,
                    params={"key": self.api_key},
                    json=search_data,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code != 200:
                    logging.error(f"❌ Error en la API: {response.status_code}")
                    logging.error(response.text)
                    continue

                data = response.json()
                properties = data.get('objects', [])
                
                logging.info(f"✅ Encontradas {len(properties)} propiedades")

                for prop in properties:
                    operations = prop.get('operations', [])
                    for operation in operations:
                        if operation.get('operation_type') == operation_type and operation.get('prices'):
                            property_info = {
                                'id': prop.get('id'),
                                'title': prop.get('publication_title'),
                                'type': prop.get('type', {}).get('name'),
                                'operation_type': operation_type,
                                'price': operation['prices'][0].get('price'),
                                'currency': operation['prices'][0].get('currency'),
                                'address': prop.get('address'),
                                'location': prop.get('location', {}).get('name'),
                                'surface': prop.get('total_surface'),
                                'rooms': prop.get('room_amount'),
                                'bathrooms': prop.get('bathroom_amount'),
                                'expenses': prop.get('expenses'),
                                'description': prop.get('description'),
                            }
                            all_properties.append(property_info)

            if all_properties:
                df = pd.DataFrame(all_properties)
                df.to_csv(self.csv_path, index=False)
                logging.info(f"\n💾 Base de datos guardada en {self.csv_path}")
                logging.info(f"📊 Total de propiedades: {len(all_properties)}")
                return True
            else:
                logging.warning("⚠️ No se encontraron propiedades")
                return False

        except Exception as e:
            logging.error(f"❌ Error: {str(e)}")
            return False

    def search_in_database(self, query: str) -> str:
        try:
            logging.info("\n" + "="*50)
            logging.info(f"🔍 BÚSQUEDA: {query}")
            logging.info("="*50)

            df = pd.read_csv(self.csv_path)
            
            # Determinar tipo de operación
            operation_type = 'Rent' if any(word in query.lower() for word in ['alquiler', 'alquilar', 'renta', 'rentar']) else 'Sale'
            
            logging.info(f"🏷️ Tipo de operación detectada: {self.operation_types[operation_type]} ({operation_type})")

            # Filtrar por tipo de operación
            results = df[df['operation_type'] == operation_type].copy()
            
            if results.empty:
                return f"No encontré propiedades en {self.operation_types[operation_type].lower()}"

            # Formatear resultados
            formatted_results = []
            for _, prop in results.iterrows():
                price = f"{prop['currency']} {prop['price']:,.0f}"
                expenses = f"(Expensas: ${prop['expenses']:,.0f})" if pd.notna(prop['expenses']) and prop['expenses'] > 0 else ""
                
                result = (
                    f"🏠 {prop['title']}\n"
                    f"💰 {price} {expenses}\n"
                    f"📍 {prop['address']}\n"
                    f"📏 {prop['surface']}m² | 🛏 {prop['rooms']} amb | 🚿 {prop['bathrooms']} baños\n"
                    f"🔍 ID: {prop['id']}\n"
                    f"➡️ Más info: https://ficha.info/p/{prop['id']}\n"
                )
                formatted_results.append(result)

            response = "\n\n".join(formatted_results[:5])  # Limitamos a 5 resultados
            logging.info(f"✅ Se encontraron {len(formatted_results)} propiedades")
            
            return response

        except Exception as e:
            logging.error(f"❌ Error: {str(e)}")
            return "Lo siento, ocurrió un error al buscar propiedades"

# Importación necesaria para el manejo de archivos
import os

if __name__ == "__main__":
    # Ejemplo de uso
    result = search_properties("departamento en alquiler en Villa Ballester")
    print(result)