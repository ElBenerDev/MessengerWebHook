from typing import Dict, List, Optional
import requests
import json
import logging
import pandas as pd
from dataclasses import dataclass
from datetime import datetime
import os

# Configuración de logging solo para consola
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('TokkoAPI')

class TokkoManager:
    def __init__(self):
        self.api_key = "34430fc661d5b961de6fd53a9382f7a232de3ef0"
        self.api_url = "https://www.tokkobroker.com/api/v1/property/search"
        self.csv_path = "properties_database.csv"

    def download_all_properties(self) -> bool:
        """Descarga todas las propiedades de Tokko y las guarda en CSV"""
        try:
            print("\n" + "="*50)
            logger.info("🔄 Iniciando descarga de propiedades desde Tokko API")
            print("="*50)

            all_properties = []
            for operation_type in ['1', '2']:  # 1=venta, 2=alquiler
                operation_name = 'venta' if operation_type == '1' else 'alquiler'
                logger.info(f"📡 Consultando propiedades en {operation_name}...")

                search_data = {
                    "current_localization_id": "25034",  # Villa Ballester
                    "current_localization_type": "division",
                    "operation_types": [operation_type],
                    "property_types": ["2", "13"],
                    "status": ["2"],
                    "with_prices": True
                }

                print(f"\n🔍 Request para {operation_name}:")
                print(json.dumps(search_data, indent=2))

                response = requests.post(
                    self.api_url,
                    params={"key": self.api_key},
                    json=search_data,
                    headers={"Content-Type": "application/json"}
                )

                logger.info(f"📊 Status API: {response.status_code}")

                if response.status_code != 200:
                    logger.error(f"❌ Error en API: {response.text}")
                    continue

                properties = response.json().get('objects', [])
                logger.info(f"✅ Recibidas {len(properties)} propiedades en {operation_name}")

                for prop in properties:
                    for operation in prop.get('operations', []):
                        if operation.get('prices'):
                            price_info = operation['prices'][0]
                            property_info = {
                                'id': prop.get('id'),
                                'title': prop.get('publication_title', ''),
                                'type': prop.get('type', {}).get('name', ''),
                                'address': prop.get('fake_address', ''),
                                'location': prop.get('location', {}).get('name', ''),
                                'operation_type': 'Alquiler' if operation_type == '2' else 'Venta',
                                'price': price_info.get('price', 0),
                                'currency': price_info.get('currency', ''),
                                'rooms': prop.get('room_amount', 0),
                                'bathrooms': prop.get('bathroom_amount', 0),
                                'total_surface': prop.get('total_surface', 0),
                                'covered_surface': prop.get('covered_surface', 0),
                                'expenses': prop.get('expenses', 0),
                                'description': prop.get('description', ''),
                                'amenities': ', '.join(prop.get('tags', [])),
                                'photos': '|'.join([p['image'] for p in prop.get('photos', [])[:3] if p.get('image')]),
                                'url': f"https://ficha.info/p/{prop.get('public_url', '').strip()}",
                                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                            all_properties.append(property_info)

            logger.info(f"📝 Creando DataFrame con {len(all_properties)} propiedades...")
            df = pd.DataFrame(all_properties)

            logger.info(f"💾 Guardando datos en {self.csv_path}...")
            df.to_csv(self.csv_path, index=False, encoding='utf-8')

            print("\n" + "="*50)
            print("📊 RESUMEN DE DATOS:")
            print("="*50)
            print(f"📍 Total propiedades: {len(df)}")
            print(f"🏠 En alquiler: {len(df[df['operation_type'] == 'Alquiler'])}")
            print(f"🏢 En venta: {len(df[df['operation_type'] == 'Venta'])}")
            print(f"💰 Precio promedio alquiler: ${df[df['operation_type'] == 'Alquiler']['price'].mean():,.2f}")
            print(f"💵 Precio promedio venta: ${df[df['operation_type'] == 'Venta']['price'].mean():,.2f}")
            print("="*50 + "\n")

            return True

        except Exception as e:
            logger.error(f"❌ Error descargando propiedades: {str(e)}")
            return False

    def search_in_database(self, query: str) -> str:
        """Busca propiedades en el CSV según los criterios del usuario"""
        try:
            print("\n" + "-"*50)
            logger.info(f"🔍 Nueva búsqueda: '{query}'")

            if not os.path.exists(self.csv_path):
                logger.info("📥 Base de datos no encontrada, descargando datos...")
                self.download_all_properties()

            if os.path.exists(self.csv_path):
                file_time = os.path.getmtime(self.csv_path)
                if (datetime.now().timestamp() - file_time) > 3600:
                    logger.info("🔄 Base de datos obsoleta, actualizando...")
                    self.download_all_properties()

            logger.info(f"📖 Leyendo base de datos desde {self.csv_path}")
            df = pd.read_csv(self.csv_path)
            logger.info(f"✅ Base de datos cargada: {len(df)} propiedades")

            operation_type = 'Alquiler'
            if any(word in query.lower() for word in ['venta', 'comprar', 'compra']):
                operation_type = 'Venta'

            logger.info(f"🏷️ Tipo de operación detectada: {operation_type}")

            results = df[df['operation_type'] == operation_type].copy()
            logger.info(f"📊 Propiedades filtradas por {operation_type}: {len(results)}")

            if 'amb' in query.lower() or 'ambiente' in query.lower():
                rooms = [int(s) for s in query.split() if s.isdigit()]
                if rooms:
                    logger.info(f"🏠 Filtrando por {rooms[0]} ambientes")
                    results = results[results['rooms'] == rooms[0]]
                    logger.info(f"✨ Propiedades después del filtro: {len(results)}")

            results = results.sort_values('price')

            if len(results) == 0:
                logger.info("❌ No se encontraron propiedades")
                return "No encontré propiedades que coincidan con tu búsqueda. ¿Quieres probar con otros criterios?"

            logger.info(f"📝 Preparando respuesta con {len(results)} propiedades")
            message = f"Encontré {len(results)} propiedades en {operation_type.lower()}:\n\n"

            for _, prop in results.head().iterrows():
                price_str = f"{prop['currency']} {prop['price']:,.0f}" if prop['price'] > 0 else "Consultar precio"

                message += f"*{prop['title']}*\n"
                message += f"📍 {prop['address']}\n"
                message += f"💰 {operation_type}: {price_str}\n"

                if prop['expenses'] > 0:
                    message += f"💵 Expensas: ${prop['expenses']:,.0f}\n"

                if prop['rooms'] > 0:
                    message += f"🏠 {prop['rooms']} ambiente{'s' if prop['rooms'] > 1 else ''}\n"

                if prop['total_surface'] > 0:
                    message += f"📐 {prop['total_surface']:.0f}m²\n"

                message += f"🔍 Ver más: {prop['url']}\n"

                photos = str(prop['photos']).split('|')
                if photos and photos[0] and photos[0] != 'nan':
                    message += f"{photos[0]}\n"

                message += "\n"

            logger.info("✅ Respuesta preparada exitosamente")
            print("-"*50 + "\n")
            return message

        except Exception as e:
            logger.error(f"❌ Error en búsqueda: {str(e)}")
            return "Lo siento, hubo un error al procesar tu búsqueda. Por favor, intenta nuevamente."

def search_properties(query: str) -> str:
    """Función principal de búsqueda"""
    manager = TokkoManager()
    return manager.search_in_database(query)

if __name__ == "__main__":
    manager = TokkoManager()

    print("\n🔥 INICIANDO SISTEMA DE BÚSQUEDA DE PROPIEDADES 🔥\n")
    logger.info("Actualizando base de datos de propiedades...")
    manager.download_all_properties()

    queries = [
        "Busco departamento en alquiler de 2 ambientes",
        "Quiero comprar un departamento",
        "Departamento en alquiler 3 ambientes"
    ]

    for query in queries:
        print(f"\n🔍 BÚSQUEDA: {query}")
        result = search_properties(query)
        print(result)

    print("\n✨ PROGRAMA FINALIZADO ✨\n")